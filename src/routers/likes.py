from typing import Sequence, Optional

from fastapi import (
    APIRouter,
    status,
    Depends,
    Query,
    HTTPException
)
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.dependencies import get_current_user
from database import get_db
from database.models.accounts import UserModel

from database.models.movies import MovieModel, LikeModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MessageResponseSchema,
)

router = APIRouter()


@router.get(
    "/movies/likes/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="List liked movies",
    description="Get a paginated list of movies liked by the current user.",
    responses={
        200: {
            "description": "List of liked movies returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "movies": [
                            {
                                "id": 1,
                                "name": "The Shawshank Redemption",
                                "year": 1994,
                                "price": 9.99,
                                "imdb": 9.3,
                                "time": 142,
                                "genres": [{"id": 1, "name": "Drama"}],
                                "stars": [{"id": 1, "name": "Tim Robbins"}],
                                "directors": [
                                    {"id": 1, "name": "Frank Darabont"}]
                            }
                        ],
                        "total_pages": 1,
                        "total_items": 1,
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
    }
)
async def get_liked_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MovieListResponseSchema:
    """Retrieve a paginated list of movies liked by the current user.

    Args:
        page (int): Page number for pagination.
        per_page (int): Number of items per page.
        sort_by (Optional[str]): Field to sort by (e.g., 'year', 'price').
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        MovieListResponseSchema: Paginated list of liked movies.
    """
    count_stmt = (
        select(func.count(MovieModel.id))
        .where(
            MovieModel.likes.any(LikeModel.user_id == user.id)
        )
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return MovieListResponseSchema(movies=[], total_pages=0, total_items=0)

    stmt = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.genres)
        )
        .where(
            MovieModel.likes.any(LikeModel.user_id == user.id)
        )
    )

    if sort_by:
        sort_field = sort_by.strip("-")
        allowed_sort_fields = ("year", "price", "imdb", "name", "time")
        if sort_field in allowed_sort_fields:
            column = getattr(MovieModel, sort_field)
            if sort_by.startswith("-"):
                stmt = stmt.order_by(desc(column))
            else:
                stmt = stmt.order_by(asc(column))

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    movies = result.scalars().all()

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    total_pages = (total_items + per_page - 1) // per_page

    return MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/cinema/movies/likes/?page={page - 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page > 1 else None,
        next_page=f"/cinema/movies/likes/?page={page + 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.post(
    "/movies/{movie_id}/likes/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Like movie",
    description="Add a like to a specific movie.",
    responses={
        200: {
            "description": "Movie liked successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Movie liked successfully."
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
        404: {
            "description": "Movie not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found"
                    }
                }
            }
        }
    }
)
async def like_movie(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Add a like to a specific movie.

    Args:
        movie_id (int): The ID of the movie to like.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        MessageResponseSchema: Success message.
    """
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    like_stmt = (
        select(LikeModel)
        .where(
            LikeModel.movie_id == movie_id,
            LikeModel.user_id == user.id
        )
    )
    result = await db.execute(like_stmt)
    like = result.scalars().first()

    if like:
        return MessageResponseSchema(message="You already like this movie.")

    new_like = LikeModel(user_id=user.id, movie_id=movie_id)
    db.add(new_like)
    await db.commit()

    return MessageResponseSchema(message="You successfully liked this movie.")


@router.delete(
    "/movies/{movie_id}/likes/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlike movie",
    description="Remove a like from a specific movie.",
    responses={
        204: {
            "description": "Movie unliked successfully"
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
        404: {
            "description": "Movie not found or not liked",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found or not liked"
                    }
                }
            }
        }
    }
)
async def unlike_movie(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove a like from a specific movie.

    Args:
        movie_id (int): The ID of the movie to unlike.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        None
    """
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    like_stmt = (
        select(LikeModel)
        .where(
            LikeModel.user_id == user.id,
            LikeModel.movie_id == movie_id
        )
    )
    result = await db.execute(like_stmt)
    like = result.scalars().first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't liked this movie yet."
        )

    await db.delete(like)
    await db.commit()

    return
