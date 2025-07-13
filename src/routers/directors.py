from typing import Sequence

from fastapi import (
    APIRouter,
    status,
    Depends,
    Query,
    HTTPException
)
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import RoleChecker
from database import get_db
from database.models.accounts import UserGroupEnum

from database.models.movies import MovieModel, DirectorModel
from schemas.movies import NameSchema, DirectorListSchema, DirectorSchema

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.get(
    "/directors/",
    response_model=DirectorListSchema,
    status_code=status.HTTP_200_OK,
    summary="List directors",
    description="Get a paginated list of all movie directors. "
                "Only moderators and admins can access.",
    responses={
        200: {
            "description": "List of directors returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "directors": [
                            {
                                "id": 1,
                                "name": "Frank Darabont"
                            },
                            {
                                "id": 2,
                                "name": "Francis Ford Coppola"
                            }
                        ],
                        "total_pages": 1,
                        "total_items": 2,
                        "prev_page": None,
                        "next_page": None
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "page"],
                                "msg": "ensure this value is greater than or equal to 1",
                                "type": "value_error.number.not_ge"
                            }
                        ]
                    }
                }
            }
        }
    },
    tags=["moderator", "directors"]
)
async def get_directors(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorListSchema:
    stmt = select(DirectorModel)

    count_stmt = (
        select(func.count(DirectorModel.id.distinct()))
        .select_from(stmt.subquery())
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return DirectorListSchema(directors=[], total_pages=0, total_items=0)

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    directors: Sequence[DirectorModel] = result.scalars().all()

    director_list = [
        DirectorSchema.model_validate(director) for director in directors
    ]

    total_pages = (total_items + per_page - 1) // per_page

    return DirectorListSchema(
        directors=director_list,
        prev_page=f"/cinema/directors/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=(
            f"/cinema/directors/?page={page + 1}"
            f"&per_page={per_page}" if page < total_pages else None
        ),
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/directors/{director_id}/",
    response_model=DirectorSchema,
    status_code=status.HTTP_200_OK,
    summary="Get director by ID",
    description="Retrieve detailed information about a specific director by their ID. "
                "Only moderators and admins can access.",
    responses={
        200: {
            "description": "Director details returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Frank Darabont"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        404: {
            "description": "Director not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director not found"
                    }
                }
            }
        }
    },
    tags=["moderator", "directors"]
)
async def get_director_by_id(
    director_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorSchema:
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director with the given id was not found."
        )

    return DirectorSchema.model_validate(director)


@router.post(
    "/directors/",
    response_model=DirectorSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create director",
    description="Create a new movie director. Only moderators and admins can perform this action.",
    responses={
        201: {
            "description": "Director created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "New Director Name"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        409: {
            "description": "Director already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director with this name already exists."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    },
    tags=["moderator", "directors"]
)
async def create_director(
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorSchema:
    stmt = select(DirectorModel).where(DirectorModel.name == data.name)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if director:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A director with the name '{data.name}' already exists."
        )

    director = DirectorModel(name=data.name.title())
    db.add(director)
    await db.commit()
    await db.refresh(director)

    return DirectorSchema.model_validate(director)


@router.patch(
    "/directors/{director_id}/",
    response_model=DirectorSchema,
    status_code=status.HTTP_200_OK,
    summary="Update director",
    description="Update an existing director's information. "
                "Only moderators and admins can perform this action.",
    responses={
        200: {
            "description": "Director updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Updated Director Name"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        404: {
            "description": "Director not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director not found"
                    }
                }
            }
        },
        409: {
            "description": "Director name already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director with this name already exists."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    },
    tags=["moderator", "directors"]
)
async def update_director(
    director_id: int,
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorSchema:
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director with the given id was not found."
        )

    try:
        director.name = data.name.title()

        await db.commit()
        await db.refresh(director)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    return DirectorSchema.model_validate(director)


@router.delete(
    "/directors/{director_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete director",
    description="Delete a director from the database. "
                "Only moderators and admins can perform this action.",
    responses={
        204: {
            "description": "Director deleted successfully"
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        404: {
            "description": "Director not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director not found"
                    }
                }
            }
        },
        409: {
            "description": "Director has associated movies",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot delete director that has associated movies."
                    }
                }
            }
        }
    },
    tags=["moderator", "directors"]
)
async def delete_director(
    director_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director with the given id was not found"
        )

    movies_check_stmt = select(func.count(MovieModel.id)).where(
        MovieModel.directors.any(DirectorModel.id == director_id)
    )
    result = await db.execute(movies_check_stmt)
    movies_count = result.scalar_one()

    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete director: {movies_count} movies are associated with it"
        )

    await db.delete(director)
    await db.commit()

    return
