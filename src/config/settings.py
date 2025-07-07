import os
from pathlib import Path
from typing import Dict, Any

from celery.schedules import crontab
from pydantic import EmailStr
from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    """Base application settings configuration.
    
    This class contains all the core configuration settings for the Online Cinema
    application, including JWT tokens, email settings, S3 storage, and Stripe
    payment configuration. It inherits from Pydantic's BaseSettings for
    automatic environment variable loading and validation.
    """
    BASE_URL: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: str = str(BASE_DIR / "database" / "source" / "online_cinema.db")

    SECRET_KEY_ACCESS: str = os.getenv(
        "SECRET_KEY_ACCESS",
        str(os.urandom(32))
    )
    SECRET_KEY_REFRESH: str = os.getenv(
        "SECRET_KEY_REFRESH",
        str(os.urandom(32))
    )
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    )
    REFRESH_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 24 * 60)
    )

    EMAIL_TEMPLATES_DIR: str = str(BASE_DIR / "notifications" / "templates")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "mailhog")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 25))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "test_user")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "some_password")
    MAIL_FROM: EmailStr = os.getenv("MAIL_FROM", "test@email.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "Test User")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "False").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"

    S3_STORAGE_HOST: str = os.getenv("MINIO_HOST", "minio-cinema")
    S3_STORAGE_PORT: int = int(os.getenv("MINIO_PORT", 9000))
    S3_STORAGE_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "test_user")
    S3_STORAGE_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "password")
    S3_BUCKET_NAME: str = os.getenv("MINIO_STORAGE", "online-cinema-storage")

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        """Get the complete S3 storage endpoint URL.
        
        Returns:
            str: The full S3 storage endpoint URL combining host and port.
        """
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"

    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY") or ""
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY") or ""


class Settings(BaseAppSettings):
    """Production settings configuration.
    
    This class inherits from BaseAppSettings and is used for production
    environment configuration. It can be extended with production-specific
    settings if needed.
    """
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "test_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "test_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "test_host")
    POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "test_db")


class TestingSettings(BaseAppSettings):
    """Development settings configuration.
    
    This class inherits from BaseAppSettings and is used for development
    environment configuration. It can be extended with development-specific
    settings if needed.
    """
    pass


class CelerySettings(BaseSettings):
    """Celery background task configuration.
    
    This class contains all the configuration settings for Celery background
    tasks, including broker URL, result backend, task imports, and scheduled
    task definitions.
    """
    broker_url: str = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0"
    )
    result_backend: str = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/1"
    )

    imports: tuple = ("tasks.tasks",)

    @property
    def beat_schedule(self) -> Dict[str, Any]:
        """Get the Celery beat schedule configuration.
        
        Defines periodic tasks that run automatically:
        - Daily cleanup of expired activation tokens
        - Daily cleanup of expired password reset tokens
        - Daily cleanup of expired refresh tokens
        
        Returns:
            Dict[str, Any]: Dictionary containing scheduled task configurations.
        """
        return {
            "delete-activation-tokens": {
                "task": "tasks.tasks.delete_expires_activation_tokens",
                "schedule": crontab(minute="0"),
            },
            "delete-password-reset-tokens": {
                "task": "tasks.tasks.delete_expires_password_reset_tokens",
                "schedule": crontab(minute="0"),
            },
            "delete-refresh-tokens": {
                "task": "tasks.tasks.delete_expires_refresh_tokens",
                "schedule": crontab(minute="0"),
            },
        }


def get_settings() -> BaseAppSettings:
    """Return the settings instance based on the ENVIRONMENT variable.
    
    If the ENVIRONMENT environment variable is set to 'testing', this function returns
    an instance of TestingSettings. For any other value (including when unset), it returns
    an instance of Settings.
    
    Returns:
        BaseAppSettings: The settings instance appropriate for the current environment.
    """
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()
