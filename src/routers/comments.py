from fastapi import (
    APIRouter,
    status,
    Depends,
    HTTPException,
    BackgroundTasks
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.dependencies import get_current_user, get_email_sender
from database import get_db
from database.models.accounts import UserGroupEnum, UserModel

from database.models.movies import MovieModel, CommentModel
from notifications.interfaces import EmailSenderInterface
from schemas.movies import CommentSchema, CommentMovieRequestSchema

router = APIRouter()


@router.post(
    "/movies/{movie_id}/comments/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to movie",
    description="Add a new comment to a specific movie.",
    responses={
        201: {
            "description": "Comment added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "text": "Amazing movie! Highly recommended.",
                        "user": {
                            "id": 1,
                            "email": "user@example.com"
                        },
                        "created_at": "2024-01-01T00:00:00Z",
                        "parent_id": None
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
                                "loc": ["body", "text"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def comment_movie(
    movie_id: int,
    data: CommentMovieRequestSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CommentSchema:
    """Add a new comment to a specific movie.

    Args:
        movie_id (int): The ID of the movie to comment on.
        data (CommentMovieRequestSchema): Comment data.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        CommentSchema: The created comment.
    """
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    comment = CommentModel(
        content=data.content,
        movie_id=movie_id,
        user_id=user.id
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentSchema.model_validate(comment)


@router.post(
    "/movies/{movie_id}/comments/{comment_id}/replies/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Reply to comment",
    description="Add a reply to an existing comment on a movie.",
    responses={
        201: {
            "description": "Reply added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 2,
                        "text": "I completely agree with your review!",
                        "user": {
                            "id": 2,
                            "email": "another@example.com"
                        },
                        "created_at": "2024-01-01T00:00:00Z",
                        "parent_id": 1
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
            "description": "Movie or comment not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie or comment not found"
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
                                "loc": ["body", "text"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def reply_to_comment(
    movie_id: int,
    comment_id: int,
    background_tasks: BackgroundTasks,
    data: CommentMovieRequestSchema,
    user: UserModel = Depends(get_current_user),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> CommentSchema:
    """Add a reply to an existing comment on a movie.

    Args:
        movie_id (int): The ID of the movie.
        comment_id (int): The ID of the comment to reply to.
        background_tasks (BackgroundTasks): FastAPI background tasks.
        data (CommentMovieRequestSchema): Reply data.
        user (UserModel): The current authenticated user.
        email_sender (EmailSenderInterface): Email sender dependency.
        db (AsyncSession): Database session dependency.

    Returns:
        CommentSchema: The created reply comment.
    """
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    parent_comment_stmt = (
        select(CommentModel)
        .options(joinedload(CommentModel.user))
        .where(
            CommentModel.id == comment_id,
            CommentModel.movie_id == movie_id
        )
    )
    result = await db.execute(parent_comment_stmt)
    parent_comment = result.scalars().first()

    if not parent_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment with the given id was not found for this movie."
        )

    reply = CommentModel(
        content=data.content,
        movie_id=movie_id,
        user_id=user.id,
        parent_id=comment_id
    )

    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    background_tasks.add_task(
        email_sender.send_comment_reply_notification_email,
        parent_comment.user.email,
        parent_comment.id,
        reply.content,
        user.email
    )

    return CommentSchema.model_validate(reply)


@router.delete(
    "/movies/{movie_id}/comments/{comment_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment",
    description="Delete a comment from a movie. "
                "Users can only delete their own comments unless they are admin/moderator.",
    responses={
        204: {
            "description": "Comment deleted successfully"
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
                        "detail": "You can only delete your own comments."
                    }
                }
            }
        },
        404: {
            "description": "Movie or comment not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie or comment not found"
                    }
                }
            }
        }
    }
)
async def delete_comment(
    movie_id: int,
    comment_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a comment from a movie.

    Args:
        movie_id (int): The ID of the movie.
        comment_id (int): The ID of the comment to delete.
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

    comment_stmt = (
        select(CommentModel)
        .where(
            CommentModel.id == comment_id,
            CommentModel.movie_id == movie_id
        )
    )
    result = await db.execute(comment_stmt)
    comment: CommentModel = result.scalars().first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment with the given id was not found for this movie."
        )

    if comment.user_id != user.id and user.group.name not in (
            UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this comment."
        )

    await db.delete(comment)
    await db.commit()

    return
