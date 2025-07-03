from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_mail import ConnectionConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.settings import BaseAppSettings, get_settings
from database import get_db
from database.models.accounts import UserModel, UserGroupEnum
from database.models.shopping_cart import CartModel
from exceptions.security import BaseSecurityError, TokenExpiredError
from notifications.emails import EmailSender
from notifications.interfaces import EmailSenderInterface
from payments.interfaces import PaymentServiceInterface
from payments.stripe import StripePaymentService
from security.interfaces import JWTManagerInterface
from security.manager import JWTManager
from storages.interfaces import S3StorageInterface
from storages.s3 import S3Storage

bearer_scheme = HTTPBearer()


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
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_user_id(
    token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager)
) -> int:
    try:
        decoded_token = jwt_manager.decode_access_token(token=token)
        user_id = decoded_token.get("user_id")
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired, please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except BaseSecurityError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db)
) -> UserModel:
    query = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.id == user_id)
    )
    result = await session.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


class RoleChecker:
    def __init__(self, allowed_groups: list[UserGroupEnum]):
        self.allowed_groups = allowed_groups

    def __call__(self, user: UserModel = Depends(get_current_user)):
        if user.group.name not in self.allowed_groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user does not have privileges to access this resource."
            )


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


async def get_or_create_cart(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> CartModel:
    cart_stmt = select(CartModel).where(CartModel.user_id == user_id)
    result = await db.execute(cart_stmt)
    cart = result.scalars().first()

    if not cart:
        cart = CartModel(user_id=user_id, items=[])
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    return cart


def get_payment_service(
    settings: BaseAppSettings = Depends(get_settings)
) -> PaymentServiceInterface:
    return StripePaymentService(
        secret_key=settings.STRIPE_SECRET_KEY,
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY
    )
