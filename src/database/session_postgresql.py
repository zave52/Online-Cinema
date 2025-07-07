from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

from config.settings import get_settings

settings = get_settings()

POSTGRESQL_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_HOST}:{settings.POSTGRES_DB_PORT}/{settings.POSTGRES_DB}"
)
postgresql_engine = create_async_engine(POSTGRESQL_DATABASE_URL, echo=False)
AsyncPostgresqlSessionLocal = async_sessionmaker(
    bind=postgresql_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

sync_database_url = POSTGRESQL_DATABASE_URL.replace(
    "postgresql+asyncpg",
    "postgresql"
)
sync_postgresql_engine = create_engine(sync_database_url, echo=False)


async def get_postgresql_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async PostgreSQL database session.
    
    This function provides a dependency injection function for FastAPI to
    get database sessions. It uses async context management to ensure
    proper session cleanup.
    
    Yields:
        AsyncSession: An async database session for PostgreSQL operations.
    """
    async with AsyncPostgresqlSessionLocal() as session:
        yield session

@asynccontextmanager
async def get_postgresql_db_contextmanager() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncPostgresqlSessionLocal() as session:
        yield session