from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from config.settings import get_settings

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
