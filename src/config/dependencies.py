import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_mail import ConnectionConfig

from config.settings import Settings, DevelopmentSettings, BaseAppSettings
from notifications.emails import EmailSender
from notifications.interfaces import EmailSenderInterface
from security.interfaces import JWTManagerInterface
from security.manager import JWTManager
from storages.interfaces import S3StorageInterface
from storages.s3 import S3Storage

bearer_scheme = HTTPBearer()


def get_settings() -> BaseAppSettings:
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "production":
        return Settings()
    return DevelopmentSettings()


def get_jwt_manager(
    settings: BaseAppSettings = Depends(get_settings)
) -> JWTManagerInterface:
    return JWTManager(
        access_secret_key=settings.SECRET_KEY_ACCESS,
        refresh_secret_key=settings.SECRET_KEY_REFRESH,
        access_expires_delta=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_expires_delta=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


async def get_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"Authorization": "Bearer"},
        )
    return credentials.credentials


def get_email_sender(
    settings: BaseAppSettings = Depends(get_settings)
) -> EmailSenderInterface:
    config = ConnectionConfig(
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        TEMPLATE_FOLDER=settings.EMAIL_TEMPLATES_DIR
    )

    return EmailSender(config=config)


def get_s3_storage(
    settings: BaseAppSettings = Depends(get_settings)
) -> S3StorageInterface:
    return S3Storage(
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        bucket_name=settings.S3_BUCKET_NAME
    )
