from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

from config.settings import get_settings
from database import Base

settings = get_settings()

SQLITE_DATABASE_URL = f"sqlite+aiosqlite:///{settings.PATH_TO_DB}"
sqlite_engine = create_async_engine(SQLITE_DATABASE_URL, echo=False)
AsyncSQLiteSessionLocal = async_sessionmaker(
    sqlite_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_sqlite_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async SQLite database session.

    This function provides a dependency injection function for FastAPI to
    get database sessions. It uses async context management to ensure
    proper session cleanup.

    Yields:
        AsyncSession: An async database session for SQLite operations.
    """
    async with AsyncSQLiteSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_sqlite_db_contextmanager() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields an async SQLite database session.

    This function is useful for scenarios where an explicit async context manager
    is required to manage the session lifecycle, such as in testing or advanced
    dependency injection patterns.

    Yields:
        AsyncSession: An async database session for SQLite operations.
    """
    async with AsyncSQLiteSessionLocal() as session:
        yield session


async def reset_sqlite_database() -> None:
    """
    Drops and recreates all tables in the SQLite database.

    This function is typically used for testing or development purposes to
    reset the database schema to its initial state by dropping all tables
    and recreating them according to the current models.

    Returns:
        None
    """
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
