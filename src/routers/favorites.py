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

from database.models.movies import MovieModel, FavoriteMovieModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MessageResponseSchema,
)

router = APIRouter()


@router.get(
    "/movies/favorites/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="List favorite movies",
    description="Get a paginated list of movies marked as favorite by the current user.",
    responses={
        200: {
            "description": "List of favorite movies returned successfully",
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
async def get_favorite_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MovieListResponseSchema:
    """Retrieve a paginated list of movies marked as favorite by the current user.

    Args:
        page (int): Page number for pagination.
        per_page (int): Number of items per page.
        sort_by (Optional[str]): Field to sort by (e.g., 'year', 'price').
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        MovieListResponseSchema: Paginated list of favorite movies.
    """
    count_stmt = (
        select(func.count(MovieModel.id))
        .where(
            MovieModel.favorites.any(FavoriteMovieModel.user_id == user.id)
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
            MovieModel.favorites.any(FavoriteMovieModel.user_id == user.id)
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
    movies: Sequence[MovieModel] = result.scalars().all()

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    total_pages = (total_items + per_page - 1) // per_page

    return MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/cinema/movies/favorites/?page={page - 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page > 1 else None,
        next_page=f"/cinema/movies/favorites/?page={page + 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.post(
    "/movies/{movie_id}/favorites/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Add movie to favorites",
    description="Add a movie to the user's favorites list.",
    responses={
        200: {
            "description": "Movie added to favorites successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Movie added to favorites successfully."
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
async def add_movie_to_favorites(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Add a movie to the user's favorites list.

    Args:
        movie_id (int): The ID of the movie to add to favorites.
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

    favorite_stmt = (
        select(FavoriteMovieModel)
        .where(
            FavoriteMovieModel.movie_id == movie_id,
            FavoriteMovieModel.user_id == user.id
        )
    )
    result = await db.execute(favorite_stmt)
    existing_favorite = result.scalars().first()

    if existing_favorite:
        return MessageResponseSchema(
            message="You have already added this movie to favorites."
        )

    new_favorite = FavoriteMovieModel(movie_id=movie_id, user_id=user.id)
    db.add(new_favorite)
    await db.commit()

    return MessageResponseSchema(
        message="You successfully added this movie to favorites."
    )


@router.delete(
    "/movies/{movie_id}/favorites/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove movie from favorites",
    description="Remove a movie from the user's favorites list.",
    responses={
        204: {
            "description": "Movie removed from favorites successfully"
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
            "description": "Movie not found or not in favorites",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found or not in favorites"
                    }
                }
            }
        }
    }
)
async def remove_movie_from_favorites(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove a movie from the user's favorites list.

    Args:
        movie_id (int): The ID of the movie to remove from favorites.
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

    favorite_stmt = (
        select(FavoriteMovieModel)
        .where(
            FavoriteMovieModel.movie_id == movie_id,
            FavoriteMovieModel.user_id == user.id
        )
    )
    result = await db.execute(favorite_stmt)
    favorite = result.scalars().first()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This movie is not in your favorites."
        )

    await db.delete(favorite)
    await db.commit()

    return
