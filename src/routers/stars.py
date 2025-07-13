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

from database.models.movies import MovieModel, StarModel
from schemas.movies import NameSchema, StarListSchema, StarSchema

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.get(
    "/stars/",
    response_model=StarListSchema,
    status_code=status.HTTP_200_OK,
    summary="List stars",
    description="Get a paginated list of all movie stars. Only moderators and admins can access.",
    responses={
        200: {
            "description": "List of stars returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "stars": [
                            {
                                "id": 1,
                                "name": "Tim Robbins"
                            },
                            {
                                "id": 2,
                                "name": "Marlon Brando"
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
    tags=["moderator", "stars"]
)
async def get_stars(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarListSchema:
    stmt = select(StarModel)

    count_stmt = (
        select(func.count(StarModel.id.distinct()))
        .select_from(stmt.subquery())
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return StarListSchema(stars=[], total_pages=0, total_items=0)

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    stars = result.scalars().all()

    star_list = [StarSchema.model_validate(star) for star in stars]

    total_pages = (total_items + per_page - 1) // per_page

    return StarListSchema(
        stars=star_list,
        prev_page=f"/cinema/stars/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=(
            f"/cinema/stars/?page={page + 1}&per_page={per_page}" if page < total_pages else None
        ),
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/stars/{star_id}/",
    response_model=StarSchema,
    status_code=status.HTTP_200_OK,
    summary="Get star by ID",
    description="Retrieve detailed information about a specific star by their ID. "
                "Only moderators and admins can access.",
    responses={
        200: {
            "description": "Star details returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Tim Robbins"
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
            "description": "Star not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star not found"
                    }
                }
            }
        }
    },
    tags=["moderator", "stars"]
)
async def get_star_by_id(
    star_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarSchema:
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star with the given id was not found."
        )

    return StarSchema.model_validate(star)


@router.post(
    "/stars/",
    response_model=StarSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create star",
    description="Create a new movie star. Only moderators and admins can perform this action.",
    responses={
        201: {
            "description": "Star created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "New Star Name"
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
            "description": "Star already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with this name already exists."
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
    tags=["moderator", "stars"]
)
async def create_star(
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarSchema:
    stmt = select(StarModel).where(StarModel.name == data.name)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if star:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A star with the name '{data.name}' already exists."
        )

    star = StarModel(name=data.name.title())
    db.add(star)
    await db.commit()
    await db.refresh(star)

    return StarSchema.model_validate(star)


@router.patch(
    "/stars/{star_id}/",
    response_model=StarSchema,
    status_code=status.HTTP_200_OK,
    summary="Update star",
    description="Update an existing star's information. "
                "Only moderators and admins can perform this action.",
    responses={
        200: {
            "description": "Star updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Updated Star Name"
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
            "description": "Star not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star not found"
                    }
                }
            }
        },
        409: {
            "description": "Star name already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with this name already exists."
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
    tags=["moderator", "stars"]
)
async def update_star(
    star_id: int,
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarSchema:
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star with the given id was not found."
        )

    try:
        star.name = data.name.title()

        await db.commit()
        await db.refresh(star)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    return StarSchema.model_validate(star)


@router.delete(
    "/stars/{star_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete star",
    description="Delete a star from the database. "
                "Only moderators and admins can perform this action.",
    responses={
        204: {
            "description": "Star deleted successfully"
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
            "description": "Star not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star not found"
                    }
                }
            }
        },
        409: {
            "description": "Star has associated movies",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot delete star that has associated movies."
                    }
                }
            }
        }
    },
    tags=["moderator", "stars"]
)
async def delete_star(
    star_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star with the given id was not found."
        )

    movies_check_stmt = select(func.count(MovieModel.id)).where(
        MovieModel.stars.any(StarModel.id == star_id)
    )
    result = await db.execute(movies_check_stmt)
    movies_count = result.scalar_one()

    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete star: {movies_count} movies are associated with it"
        )

    await db.delete(star)
    await db.commit()

    return
