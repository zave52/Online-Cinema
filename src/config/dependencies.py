import os
from urllib.parse import urljoin

from fastapi import Depends, Request, HTTPException, status
from fastapi_mail import ConnectionConfig

from config.settings import Settings, DevelopmentSettings, BaseAppSettings
from notifications.emails import EmailSender
from notifications.interfaces import EmailSenderInterface
from security.interfaces import JWTManagerInterface
from security.manager import JWTManager
from storages.interfaces import S3StorageInterface
from storages.s3 import S3Storage


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


def get_token(request: Request) -> str:
    authorization: str = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing."
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )

    return token


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
