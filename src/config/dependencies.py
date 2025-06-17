import os

from fastapi import Depends, Request, HTTPException, status

from config.settings import Settings, DevelopmentSettings, BaseAppSettings
from security.interfaces import JWTManagerInterface
from security.manager import JWTManager


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
