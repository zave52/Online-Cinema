from fastapi import (
    APIRouter,
    status,
    Depends,
    HTTPException
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from database import get_db
from database.models.accounts import UserModel
from database.models.movies import MovieModel, RateMovieModel
from schemas.movies import MessageResponseSchema, RateMovieSchema

router = APIRouter()


@router.post(
    "/movies/{movie_id}/rates/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Rate movie",
    description="Rate a movie with a score from 1 to 10. "
                "If already rated, updates the existing rating.",
    responses={
        200: {
            "description": "Movie rated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Movie rated successfully with score 9."
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
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "score"],
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
async def rate_movie(
    movie_id: int,
    data: RateMovieSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Rate a movie with a score from 1 to 10.

    Args:
        movie_id (int): The ID of the movie to rate.
        data (RateMovieSchema): Rating data (score from 1-10).
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        MessageResponseSchema: Success message with rating information.
    """
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    rate_stmt = (
        select(RateMovieModel)
        .where(
            RateMovieModel.movie_id == movie_id,
            RateMovieModel.user_id == user.id
        )
    )
    result = await db.execute(rate_stmt)
    existing_rate: RateMovieModel | None = result.scalars().first()

    if existing_rate:
        previous_rate = existing_rate.rate
        existing_rate.rate = data.rate
        await db.commit()

        return MessageResponseSchema(
            message=f"You changed your rating for the movie "
                    f"from {previous_rate} to {existing_rate.rate}."
        )

    new_rate = RateMovieModel(
        rate=data.rate,
        movie_id=movie_id,
        user_id=user.id
    )
    db.add(new_rate)
    await db.commit()

    return MessageResponseSchema(
        message=f"You gave the movie a rating of {new_rate.rate}."
    )


@router.delete(
    "/movies/{movie_id}/rates/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete movie rating",
    description="Remove the user's rating for a specific movie.",
    responses={
        204: {
            "description": "Rating deleted successfully"
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
            "description": "Movie not found or not rated",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found or not rated"
                    }
                }
            }
        }
    }
)
async def delete_rate(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove the user's rating for a specific movie.

    Args:
        movie_id (int): The ID of the movie to remove rating from.
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

    rate_stmt = (
        select(RateMovieModel)
        .where(
            RateMovieModel.movie_id == movie_id,
            RateMovieModel.user_id == user.id
        )
    )
    result = await db.execute(rate_stmt)
    rate: RateMovieModel | None = result.scalars().first()

    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't rated this movie yet."
        )

    await db.delete(rate)
    await db.commit()

    return
