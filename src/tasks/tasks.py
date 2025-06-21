from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from .celery_app import async_task
from database import AsyncSessionLocal
from database.models.accounts import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)


@async_task()
async def delete_expires_activation_tokens() -> None:
    async with AsyncSessionLocal() as session:
        session: AsyncSession
        stmt = (
            delete(ActivationTokenModel)
            .where(ActivationTokenModel.expires_at < datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        await session.execute(stmt)
        await session.commit()


@async_task()
async def delete_expires_password_reset_tokens() -> None:
    async with AsyncSessionLocal() as session:
        session: AsyncSession
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
    async with AsyncSessionLocal() as session:
        session: AsyncSession
        stmt = (
            delete(RefreshTokenModel)
            .where(RefreshTokenModel.expires_at < datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        await session.execute(stmt)
        await session.commit()
