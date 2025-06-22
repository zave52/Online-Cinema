import os

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "production":
    pass
else:
    from .session_sqlite import (
        get_sqlite_db as get_db,
        AsyncSQLiteSessionLocal as AsyncSessionLocal
    )
