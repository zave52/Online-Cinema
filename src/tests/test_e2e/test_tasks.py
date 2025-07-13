from datetime import datetime, timedelta, timezone
from typing import cast

import pytest
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserModel,
    UserGroupModel,
    UserGroupEnum
)
from tasks.tasks import (
    delete_expires_activation_tokens,
    delete_expires_password_reset_tokens,
    delete_expires_refresh_tokens,
)


@pytest.mark.e2e
@pytest.mark.order(10)
@pytest.mark.asyncio
async def test_delete_expired_activation_tokens(
    e2e_db_session: AsyncSession,
    monkeypatch
):
    """Test that expired activation tokens are deleted."""
    user_group = await e2e_db_session.execute(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    user_group = user_group.scalar_one()
    user = UserModel.create(
        email=cast(EmailStr, "expired.activation@example.com"),
        raw_password="StrongPassword123!",
        group_id=user_group.id
    )
    e2e_db_session.add(user)
    await e2e_db_session.flush()

    expired_token = ActivationTokenModel(
        token="expired_token",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    e2e_db_session.add(expired_token)
    await e2e_db_session.commit()

    result = await e2e_db_session.execute(
        select(ActivationTokenModel).where(
            ActivationTokenModel.token == "expired_token"
        )
    )
    print(result.scalars().all())

    monkeypatch.setattr("tasks.tasks.AsyncSessionLocal", lambda: e2e_db_session)

    await delete_expires_activation_tokens()

    result = await e2e_db_session.execute(
        select(ActivationTokenModel).where(
            ActivationTokenModel.token == "expired_token"
        )
    )
    assert result.scalars().first() is None


@pytest.mark.e2e
@pytest.mark.order(11)
@pytest.mark.asyncio
async def test_delete_expired_password_reset_tokens(
    e2e_db_session: AsyncSession,
    monkeypatch
):
    """Test that expired password reset tokens are deleted."""
    user_group = await e2e_db_session.execute(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    user_group = user_group.scalar_one()
    user = UserModel.create(
        email=cast(EmailStr, "expired.password.reset@example.com"),
        raw_password="StrongPassword123!",
        group_id=user_group.id
    )
    e2e_db_session.add(user)
    await e2e_db_session.flush()

    expired_token = PasswordResetTokenModel(
        token="expired_token",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    e2e_db_session.add(expired_token)
    await e2e_db_session.commit()

    result = await e2e_db_session.execute(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token == "expired_token"
        )
    )
    print(result.scalars().all())

    monkeypatch.setattr("tasks.tasks.AsyncSessionLocal", lambda: e2e_db_session)

    await delete_expires_password_reset_tokens()

    result = await e2e_db_session.execute(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token == "expired_token"
        )
    )
    assert result.scalars().first() is None


@pytest.mark.e2e
@pytest.mark.order(12)
@pytest.mark.asyncio
async def test_delete_expired_refresh_tokens(
    e2e_db_session: AsyncSession,
    monkeypatch
):
    """Test that expired refresh tokens are deleted."""
    user_group = await e2e_db_session.execute(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    user_group = user_group.scalar_one()
    user = UserModel.create(
        email=cast(EmailStr, "expired.refresh@example.com"),
        raw_password="StrongPassword123!",
        group_id=user_group.id
    )
    e2e_db_session.add(user)
    await e2e_db_session.flush()

    expired_token = RefreshTokenModel(
        token="expired_token",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    e2e_db_session.add(expired_token)
    await e2e_db_session.commit()

    monkeypatch.setattr("tasks.tasks.AsyncSessionLocal", lambda: e2e_db_session)

    await delete_expires_refresh_tokens()

    result = await e2e_db_session.execute(
        select(RefreshTokenModel).where(
            RefreshTokenModel.token == "expired_token"
        )
    )
    assert result.scalars().first() is None
