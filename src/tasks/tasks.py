from datetime import datetime, timezone

from sqlalchemy import delete

from .celery_app import async_task
from database import AsyncSessionLocal
from database.models.accounts import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)


@async_task()
async def delete_expires_activation_tokens() -> None:
    """Delete expired activation tokens from the database.
    
    This task removes all activation tokens that have passed their
    expiration time, helping to keep the database clean and secure.
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            delete(ActivationTokenModel)
            .where(ActivationTokenModel.expires_at < datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        await session.execute(stmt)
        await session.commit()


@async_task()
async def delete_expires_password_reset_tokens() -> None:
    """Delete expired password reset tokens from the database.
    
    This task removes all password reset tokens that have passed their
    expiration time, helping to keep the database clean and secure.
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            delete(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.expires_at < datetime.now(timezone.utc)
            )
            .execution_options(synchronize_session=False)
        )
        await session.execute(stmt)
        await session.commit()


@async_task()
async def delete_expires_refresh_tokens() -> None:
    """Delete expired refresh tokens from the database.
    
    This task removes all refresh tokens that have passed their
    expiration time, helping to keep the database clean and secure.
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            delete(RefreshTokenModel)
            .where(RefreshTokenModel.expires_at < datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        await session.execute(stmt)
        await session.commit()
