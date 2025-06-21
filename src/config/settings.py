import os
from pathlib import Path

from pydantic import EmailStr, SecretStr, HttpUrl
from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    BASE_URL: HttpUrl = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: str = str(BASE_DIR / "database" / "source" / "cinema.db")

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
    MAIL_PASSWORD: SecretStr = os.getenv("MAIL_PASSWORD", "some_password")
    MAIL_FROM: EmailStr = os.getenv("MAIL_FROM", "test@email.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "Test User")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "False").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"

    S3_STORAGE_HOST: str = os.getenv("MINIO_HOST", "minio-cinema")
    S3_STORAGE_PORT: int = os.getenv("MINIO_PORT", 9000)
    S3_STORAGE_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "test_user")
    S3_STORAGE_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "password")
    S3_BUCKET_NAME: str = os.getenv("MINIO_STORAGE", "online-cinema-storage")

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"


class Settings(BaseAppSettings):
    pass


class DevelopmentSettings(BaseAppSettings):
    pass
