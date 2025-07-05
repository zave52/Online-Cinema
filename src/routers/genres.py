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

from database.models.movies import MovieModel, GenreModel
from schemas.movies import (
    NameSchema,
    GenreSchema,
    GenreListSchema,
    GenreWithMovieCountSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.get(
    "/genres/",
    response_model=GenreListSchema,
    status_code=status.HTTP_200_OK,
    summary="List genres",
    description="Get a paginated list of all movie genres. Only moderators and admins can access.",
    responses={
        200: {
            "description": "List of genres returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "genres": [
                            {
                                "id": 1,
                                "name": "Drama",
                                "movie_count": 15
                            },
                            {
                                "id": 2,
                                "name": "Action",
                                "movie_count": 12
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
    tags=["moderator", "genres"]
)
async def get_genres(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreListSchema:
    subquery = (
        select(
            GenreModel.id,
            func.count(MovieModel.id).label("movie_count")
        )
        .join(MovieModel.genres)
        .group_by(GenreModel.id)
        .subquery()
    )

    stmt = (
        select(GenreModel, subquery.c.movie_count)
        .outerjoin(subquery, GenreModel.id == subquery.c.id)
    )

    count_stmt = select(func.count(GenreModel.id))
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return GenreListSchema(genres=[], total_pages=0, total_items=0)

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page).order_by(GenreModel.name)
    result = await db.execute(stmt)
    genres_with_counts = result.all()

    genre_list = [
        GenreWithMovieCountSchema(
            id=genre.id,
            name=genre.name,
            movie_count=count or 0
        )
        for genre, count in genres_with_counts
    ]

    total_pages = (total_items + per_page - 1) // per_page

    return GenreListSchema(
        genres=genre_list,
        prev_page=f"/cinema/genres/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/genres/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/genres/{genre_id}/",
    response_model=GenreWithMovieCountSchema,
    status_code=status.HTTP_200_OK,
    summary="Get genre by ID",
    description="Retrieve detailed information about a specific genre by its ID. Only moderators and admins can access.",
    responses={
        200: {
            "description": "Genre details returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Drama",
                        "movie_count": 15
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
            "description": "Genre not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre not found"
                    }
                }
            }
        }
    },
    tags=["moderator", "genres"]
)
async def get_genre_by_id(
    genre_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreWithMovieCountSchema:
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre: GenreModel = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given id was not found."
        )

    movie_count_stmt = (
        select(func.count(MovieModel.id))
        .where(MovieModel.genres.any(GenreModel.id == genre_id))
    )
    result = await db.execute(movie_count_stmt)
    movie_count = result.scalar_one()

    return GenreWithMovieCountSchema(
        id=genre_id,
        name=genre.name,
        movie_count=movie_count
    )


@router.post(
    "/genres/",
    response_model=GenreSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create genre",
    description="Create a new movie genre. Only moderators and admins can perform this action.",
    responses={
        201: {
            "description": "Genre created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Thriller"
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
            "description": "Genre already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with this name already exists."
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
    tags=["moderator", "genres"]
)
async def create_genre(
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreSchema:
    stmt = select(GenreModel).where(GenreModel.name == data.name)
    result = await db.execute(stmt)
    existing_genre = result.scalars().first()

    if existing_genre:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A genre with the name '{data.name}' already exists."
        )

    genre = GenreModel(name=data.name.title())
    db.add(genre)
    await db.commit()
    await db.refresh(genre)

    return GenreSchema.model_validate(genre)


@router.patch(
    "/genres/{genre_id}/",
    response_model=GenreSchema,
    status_code=status.HTTP_200_OK,
    summary="Update genre",
    description="Update an existing genre's information. Only moderators and admins can perform this action.",
    responses={
        200: {
            "description": "Genre updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Updated Genre Name"
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
            "description": "Genre not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre not found"
                    }
                }
            }
        },
        409: {
            "description": "Genre name already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with this name already exists."
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
    tags=["moderator", "genres"]
)
async def update_genre(
    genre_id: int,
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreSchema:
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre: GenreModel = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given id was not found."
        )

    try:
        genre.name = data.name.title()

        await db.commit()
        await db.refresh(genre)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    return GenreSchema.model_validate(genre)


@router.delete(
    "/genres/{genre_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete genre",
    description="Delete a genre from the database. Only moderators and admins can perform this action.",
    responses={
        204: {
            "description": "Genre deleted successfully"
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
            "description": "Genre not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre not found"
                    }
                }
            }
        },
        409: {
            "description": "Genre has associated movies",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot delete genre that has associated movies."
                    }
                }
            }
        }
    },
    tags=["moderator", "genres"]
)
async def delete_genre(
    genre_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given id was not found."
        )

    movies_check_stmt = select(func.count(MovieModel.id)).where(
        MovieModel.genres.any(GenreModel.id == genre_id)
    )
    result = await db.execute(movies_check_stmt)
    movies_count = result.scalar_one()

    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete genre: {movies_count} movies are associated with it"
        )

    await db.delete(genre)
    await db.commit()

    return
