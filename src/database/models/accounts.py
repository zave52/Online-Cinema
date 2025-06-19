from enum import Enum
from typing import List, Optional, cast
from datetime import datetime, timezone, timedelta

from pydantic import EmailStr
from sqlalchemy import (
    Integer,
    Enum as SqlEnum,
    String,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from base import Base
from database.validators.accounts import (
    validate_email,
    validate_password_strength
)
from security.utils import verify_password, hash_password, generate_secure_token


class UserGroupEnum(Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroupModel(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[UserGroupEnum] = mapped_column(
        SqlEnum(UserGroupEnum), nullable=False, unique=True
    )

    users: Mapped[List["UserModel"]] = relationship(
        "UserModel", back_populates="group"
    )

    def __repr__(self) -> str:
        return f"<UserGroupModel(id={self.id}, name={self.name})>"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    email: Mapped[EmailStr] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    _hashed_password: Mapped[str] = mapped_column(
        "hashed_password", String(255), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"),
        nullable=False
    )
    group: Mapped[UserGroupModel] = relationship(
        UserGroupModel,
        back_populates="users"
    )

    profile: Mapped[Optional["UserProfileModel"]] = relationship(
        "UserProfileModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    activation_token: Mapped[Optional["ActivationTokenModel"]] = relationship(
        "ActivationTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    password_refresh_token: Mapped[
        Optional["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    refresh_token: Mapped[Optional["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email={self.email}, is_active={self.is_active})>"

    def has_group(self, group_name: UserGroupEnum) -> bool:
        return self.group.name == group_name

    @classmethod
    def create(
        cls, email: EmailStr, raw_password: str, group_id: int | Mapped[int]
    ) -> "UserModel":
        user = cls(email=email, group_id=group_id)
        user.password = raw_password
        return user

    @property
    def password(self) -> None:
        raise AttributeError(
            "Password is write-only. Use the setter to set the password."
        )

    @password.setter
    def password(self, raw_password: str) -> None:
        validate_password_strength(raw_password)
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email_field(self, field_name: str, email: str) -> str:
        return validate_email(email.lower())


class TokenBaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        default=generate_secure_token
    )
    expired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    def is_expired(self) -> bool:
        return cast(datetime, self.expired_at).replace(
            tzinfo=timezone.utc
        ) < datetime.now(timezone.utc)


class ActivationTokenModel(TokenBaseModel):
    __tablename__ = "activation_tokens"

    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="activation_token",
        cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self) -> str:
        return f"<ActivationTokenModel(id={self.id}, token={self.token}, expired_at={self.expired_at})>"


class PasswordResetTokenModel(TokenBaseModel):
    __tablename__ = "password_reset_tokens"

    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="password_reset_token",
        cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self) -> str:
        return f"<PasswordResetTokenModel(id={self.id}, token={self.token}, expired_at={self.expired_at})>"


class RefreshTokenModel(TokenBaseModel):
    __tablename__ = "refresh_tokens"

    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="refresh_token",
        cascade="all, delete-orphan"
    )
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        default=generate_secure_token
    )

    @classmethod
    def create(
        cls, user_id: int | Mapped[int], minutes_valid: int, token: str
    ) -> "RefreshTokenModel":
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=minutes_valid
        )
        return cls(user_id=user_id, token=token, expires_at=expires_at)

    def __repr__(self) -> str:
        return f"<RefreshTokenModel(id={self.id}, token={self.token}, expired_at={self.expired_at})>"
