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
    UniqueConstraint,
    Table,
    Column
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database.models.base import Base
from database.validators.accounts import (
    validate_email,
    validate_password_strength
)
from security.utils import verify_password, hash_password, generate_secure_token

purchased_movies_association = Table(
    "purchased_movies",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class UserGroupEnum(Enum):
    """Enumeration for user group types.
    
    Defines the different user groups in the system:
    - USER: Regular user with basic permissions
    - MODERATOR: User with moderation capabilities
    - ADMIN: Administrator with full system access
    """
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(Enum):
    """Enumeration for user gender options.
    
    Defines the gender options for user profiles:
    - MAN: Male
    - WOMAN: Female
    """
    MAN = "man"
    WOMAN = "woman"


class UserGroupModel(Base):
    """Model representing user groups in the system.
    
    This model stores different user groups that determine permissions
    and access levels for users in the application.
    """
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
    """User model representing registered users in the system.
    
    This model handles user authentication, profile management, and relationships
    with other entities like movies, orders, and payments.
    """
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
    password_reset_token: Mapped[
        Optional["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    likes: Mapped[List["LikeModel"]] = relationship(
        "LikeModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    comments: Mapped[List["CommentModel"]] = relationship(
        "CommentModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    favorite_movies: Mapped[List["FavoriteMovieModel"]] = relationship(
        "FavoriteMovieModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    rate_movies: Mapped[List["RateMovieModel"]] = relationship(
        "RateMovieModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    purchased: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        backref="purchasers",
        cascade="all, delete",
        secondary=purchased_movies_association
    )
    cart: Mapped["CartModel"] = relationship(
        "CartModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    orders: Mapped[List["OrderModel"]] = relationship(
        "OrderModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    payments: Mapped[List["PaymentModel"]] = relationship(
        "PaymentModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email={self.email}, is_active={self.is_active})>"

    def has_group(self, group_name: UserGroupEnum) -> bool:
        """Check if the user belongs to a specific group.
        
        Args:
            group_name (UserGroupEnum): The group to check for.
            
        Returns:
            bool: True if user belongs to the specified group, False otherwise.
        """
        return self.group.name == group_name

    @classmethod
    def create(
        cls, email: EmailStr, raw_password: str, group_id: int | Mapped[int]
    ) -> "UserModel":
        """Create a new user instance with hashed password.
        
        Args:
            email (EmailStr): User's email address.
            raw_password (str): Plain text password to be hashed.
            group_id (int | Mapped[int]): ID of the user's group.
            
        Returns:
            UserModel: New user instance with hashed password.
        """
        user = cls(email=email, group_id=group_id)
        user.password = raw_password
        return user

    @property
    def password(self) -> None:
        """Password property getter - raises error as password is write-only.
        
        Raises:
            AttributeError: Always raised as password is write-only for security.
        """
        raise AttributeError(
            "Password is write-only. Use the setter to set the password."
        )

    @password.setter
    def password(self, raw_password: str) -> None:
        """Set the user's password with validation and hashing.
        
        Args:
            raw_password (str): Plain text password to be validated and hashed.
        """
        validate_password_strength(raw_password)
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """Verify a plain text password against the stored hash.
        
        Args:
            raw_password (str): Plain text password to verify.
            
        Returns:
            bool: True if password matches, False otherwise.
        """
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email_field(self, field_name: str, email: str) -> str:
        """Validate email field using custom validation logic.
        
        Args:
            field_name (str): Name of the field being validated.
            email (str): Email address to validate.
            
        Returns:
            str: Validated email address.
        """
        return validate_email(email)


class TokenBaseModel(Base):
    """Base model for all token types in the system.
    
    This abstract base class provides common functionality for all token
    models including activation tokens, password reset tokens, and refresh tokens.
    """
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
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    def is_expired(self) -> bool:
        """Check if the token has expired.
        
        Compares the token's expiration time with the current UTC time.
        
        Returns:
            bool: True if token has expired, False otherwise.
        """
        return cast(datetime, self.expires_at).replace(
            tzinfo=timezone.utc
        ) < datetime.now(timezone.utc)


class ActivationTokenModel(TokenBaseModel):
    """Model representing user account activation tokens.
    
    This model stores tokens used for email verification and account activation.
    Each user can have only one activation token at a time.
    """
    __tablename__ = "activation_tokens"

    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="activation_token"
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self) -> str:
        return f"<ActivationTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class PasswordResetTokenModel(TokenBaseModel):
    """Model representing password reset tokens.
    
    This model stores tokens used for password reset functionality.
    Each user can have only one password reset token at a time.
    """
    __tablename__ = "password_reset_tokens"

    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="password_reset_token"
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self) -> str:
        return f"<PasswordResetTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class RefreshTokenModel(TokenBaseModel):
    """Model representing JWT refresh tokens.
    
    This model stores refresh tokens used for JWT authentication.
    Users can have multiple refresh tokens for different sessions.
    """
    __tablename__ = "refresh_tokens"

    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="refresh_tokens"
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
        """Create a new refresh token with custom expiration time.
        
        Args:
            user_id (int | Mapped[int]): ID of the user the token belongs to.
            minutes_valid (int): Number of minutes the token should be valid.
            token (str): The refresh token string.
            
        Returns:
            RefreshTokenModel: New refresh token instance.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=minutes_valid
        )
        return cls(user_id=user_id, token=token, expires_at=expires_at)

    def __repr__(self) -> str:
        return f"<RefreshTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"
