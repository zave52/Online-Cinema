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
        AsyncSQLiteSessionLocal as AsyncSessionLocal
    )
