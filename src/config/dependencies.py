from pathlib import Path
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_mail import ConnectionConfig
from pydantic import SecretStr
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
    """Get JWT manager instance with application settings.
    
    Creates and returns a JWT manager configured with the application's
    secret keys, token expiration times, and signing algorithm.
    
    Args:
        settings (BaseAppSettings): Application settings containing JWT configuration.
        
    Returns:
        JWTManagerInterface: Configured JWT manager instance.
    """
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
    """Extract JWT token from HTTP Authorization header.
    
    Validates that the request contains a Bearer token in the Authorization header
    and returns the token string.
    
    Args:
        credentials (HTTPAuthorizationCredentials): The HTTP authorization credentials.
        
    Returns:
        str: The JWT token from the Authorization header.
        
    Raises:
        HTTPException: If no credentials are provided (401 Unauthorized).
    """
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
    """Get the current user ID from JWT token.
    
    Decodes the JWT token and extracts the user ID. Handles token expiration
    and validation errors by raising appropriate HTTP exceptions.
    
    Args:
        token (str): The JWT token to decode.
        jwt_manager (JWTManagerInterface): JWT manager for token decoding.
        
    Returns:
        int: The user ID from the decoded token.
        
    Raises:
        HTTPException: If token is expired or invalid (401 Unauthorized).
    """
    try:
        decoded_token = jwt_manager.decode_access_token(token=token)
        user_id = decoded_token.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
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
    """Get the current authenticated user from database.
    
    Retrieves the user from the database using the user ID from the JWT token.
    Includes the user's group information for authorization purposes.
    
    Args:
        user_id (int): The user ID from the JWT token.
        session (AsyncSession): Database session for querying user data.
        
    Returns:
        UserModel: The authenticated user with group information.
        
    Raises:
        HTTPException: If user is not found (401 Unauthorized).
    """
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
    """Role-based access control checker.
    
    This class provides role-based authorization by checking if the current
    user belongs to one of the allowed user groups.
    """
    
    def __init__(self, allowed_groups: list[UserGroupEnum]):
        """Initialize the role checker with allowed groups.
        
        Args:
            allowed_groups (list[UserGroupEnum]): List of user groups that are
                allowed to access the protected resource.
        """
        self.allowed_groups = allowed_groups

    def __call__(self, user: UserModel = Depends(get_current_user)):
        """Check if the current user has the required role.
        
        Args:
            user (UserModel): The current authenticated user.
            
        Raises:
            HTTPException: If user doesn't have required privileges (403 Forbidden).
        """
        if user.group.name not in self.allowed_groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user does not have privileges to access this resource."
            )


def get_email_sender(
    settings: BaseAppSettings = Depends(get_settings)
) -> EmailSenderInterface:
    """Get email sender instance with application settings.
    
    Creates and returns an email sender configured with the application's
    email server settings and template directory.
    
    Args:
        settings (BaseAppSettings): Application settings containing email configuration.
        
    Returns:
        EmailSenderInterface: Configured email sender instance.
    """
    config = ConnectionConfig(
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        TEMPLATE_FOLDER=Path(settings.EMAIL_TEMPLATES_DIR)
    )

    return EmailSender(config=config)


def get_s3_storage(
    settings: BaseAppSettings = Depends(get_settings)
) -> S3StorageInterface:
    """Get S3 storage instance with application settings.
    
    Creates and returns an S3 storage client configured with the application's
    storage settings including access keys, endpoint, and bucket name.
    
    Args:
        settings (BaseAppSettings): Application settings containing S3 configuration.
        
    Returns:
        S3StorageInterface: Configured S3 storage instance.
    """
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
    """Get or create a shopping cart for the current user.
    
    Retrieves the user's existing shopping cart from the database. If no cart
    exists, creates a new one and returns it.
    
    Args:
        user_id (int): The current user's ID.
        db (AsyncSession): Database session for cart operations.
        
    Returns:
        CartModel: The user's shopping cart (existing or newly created).
    """
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
    """Get payment service instance with application settings.
    
    Creates and returns a Stripe payment service configured with the application's
    Stripe API keys.
    
    Args:
        settings (BaseAppSettings): Application settings containing Stripe configuration.
        
    Returns:
        PaymentServiceInterface: Configured Stripe payment service instance.
    """
    return StripePaymentService(
        secret_key=settings.STRIPE_SECRET_KEY,
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY
    )
