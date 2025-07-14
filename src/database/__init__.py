"""Database module for the Online Cinema application.

This module provides database configuration and session management for the
application. It supports different database backends based on the environment:

- Development: SQLite with async support
- Production: Configurable for other databases (PostgreSQL, MySQL, etc.)

The module exports:
- get_db: Dependency injection function for database sessions
- AsyncSessionLocal: Session factory for async database operations
- All database models and migrations
"""
import os

from database.models.accounts import (
    purchased_movies_association,
    UserGroupEnum,
    GenderEnum,
    UserGroupModel,
    UserModel,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)
from database.models.base import Base
from database.models.movies import (
    movie_genre_association,
    movie_star_association,
    movie_director_association,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel,
    MovieModel,
    LikeModel,
    CommentModel,
    FavoriteMovieModel,
    RateMovieModel
)
from database.models.orders import OrderStatusEnum, OrderModel, OrderItemModel
from database.models.payments import (
    PaymentStatusEnum,
    PaymentModel,
    PaymentItemModel
)
from database.models.profiles import UserProfileModel
from database.models.shopping_cart import CartModel, CartItemModel
from database.session_sqlite import reset_sqlite_database as reset_database

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "developing":
    from database.session_postgresql import (
        get_postgresql_db as get_db,
        AsyncPostgresqlSessionLocal as AsyncSessionLocal,
        get_postgresql_db_contextmanager as get_db_contextmanager,
        sync_postgresql_engine as sync_db_engine
    )
else:
    from .session_sqlite import (
        get_sqlite_db as get_db,
        AsyncSQLiteSessionLocal as AsyncSessionLocal,
        get_sqlite_db_contextmanager as get_db_contextmanager
    )
