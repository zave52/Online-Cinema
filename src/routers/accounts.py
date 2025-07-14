from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.dependencies import (
    get_email_sender,
    get_jwt_manager,
    get_settings,
    get_token,
    get_current_user, RoleChecker
)
from config.settings import BaseAppSettings
from database import get_db
from database.models.accounts import (
    UserModel,
    UserGroupModel,
    ActivationTokenModel,
    UserGroupEnum,
    PasswordResetTokenModel,
    RefreshTokenModel
)
from exceptions.security import BaseSecurityError
from notifications.interfaces import EmailSenderInterface

from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    MessageResponseSchema,
    UserActivationRequestSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema,
    UserLoginResponseSchema,
    UserLoginRequestSchema,
    TokenRefreshResponseSchema,
    TokenRefreshRequestSchema,
    TokenVerifyRequestSchema,
    ResendActivationTokenRequestSchema,
    PasswordChangeRequestSchema,
    UserGroupUpdateRequestSchema,
    UserManualActivationSchema
)
from security.interfaces import JWTManagerInterface

router = APIRouter()

admin_only = RoleChecker([UserGroupEnum.ADMIN])


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new user with email and password. "
                "Sends an activation email with a token.",
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "is_active": False,
                        "created_at": "2024-01-01T00:00:00Z",
                        "group": {
                            "id": 1,
                            "name": "user"
                        }
                    }
                }
            }
        },
        409: {
            "description": "User with this email already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email user@example.com already exists."
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during user creation",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during user creation."
                    }
                }
            }
        }
    },
)
async def register_user(
    data: UserRegistrationRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> UserRegistrationResponseSchema:
    """Register a new user and send an activation email.

    Args:
        data: Registration data (email, password).
        background_tasks: FastAPI background tasks for sending email.
        settings: Application settings.
        email_sender: Email sender service.
        db: Database session.

    Returns:
        UserRegistrationResponseSchema: The registered user data.
    """
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {data.email} already exists."
        )

    stmt = select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.USER
    )
    result = await db.execute(stmt)
    user_group = result.scalars().first()

    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found."
        )

    try:
        new_user = UserModel.create(
            email=data.email,
            raw_password=data.password,
            group_id=user_group.id
        )
        db.add(new_user)
        await db.flush()

        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)

        await db.commit()
        await db.refresh(activation_token)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation."
        ) from e
    else:
        activation_link = (
            f"{settings.BASE_URL}/activate/"
            f"?email={new_user.email}&token={activation_token.token}"
        )

        background_tasks.add_task(
            email_sender.send_activation_email,
            new_user.email,
            activation_link
        )

    return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/activate/resend/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Resend activation token",
    description="Resend a new activation token to the user's email if the previous one expired.",
    responses={
        200: {
            "description": "Activation token resent successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "If your account exists and is not activated, "
                                   "you will receive an email with instructions."
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during token resend",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during resending activation token."
                    }
                }
            }
        }
    },
)
async def resend_activation_token(
    data: ResendActivationTokenRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Resend a new activation token to the user's email if the previous one expired.

    Args:
        data: Email for which to resend the activation token.
        background_tasks: FastAPI background tasks for sending email.
        settings: Application settings.
        email_sender: Email sender service.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    standard_response = MessageResponseSchema(
        message="If your account exists and is not activated, "
                "you will receive an email with instructions."
    )

    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel | None = result.scalars().first()

    if not user or user.is_active:
        return standard_response

    if user:
        await db.execute(
            delete(ActivationTokenModel)
            .where(ActivationTokenModel.user_id == user.id)
        )

    try:
        new_activation_token = ActivationTokenModel(user_id=user.id)
        db.add(new_activation_token)
        await db.commit()
        await db.refresh(new_activation_token)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during resending activation token."
        )
    else:
        activation_link = (
            f"{settings.BASE_URL}/activate/"
            f"?email={user.email}&token={new_activation_token.token}"
        )

        background_tasks.add_task(
            email_sender.send_activation_email,
            user.email,
            activation_link
        )

    return standard_response


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Activate user account",
    description="Activate a user account using the activation token sent via email.",
    responses={
        200: {
            "description": "User account activated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User account activated successfully."
                    }
                }
            }
        },
        400: {
            "description": "Invalid or expired activation token or user already active",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or expired activation token."
                            }
                        },
                        "already_active": {
                            "summary": "Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        }
                    }
                }
            }
        }
    },
)
async def activate_account(
    data: UserActivationRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Activate a user account using the activation token sent via email.

    Args:
        data: Activation token and email.
        background_tasks: FastAPI background tasks for sending email.
        settings: Application settings.
        email_sender: Email sender service.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .join(UserModel).where(
            ActivationTokenModel.token == data.token,
            UserModel.email == data.email
        )
    )
    result = await db.execute(stmt)
    token_record: ActivationTokenModel | None = result.scalars().first()

    if not token_record or token_record.is_expired():
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )

    user: UserModel = token_record.user

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    login_link = f"{settings.BASE_URL}/login/"

    background_tasks.add_task(
        email_sender.send_activation_complete_email,
        user.email,
        login_link
    )

    return MessageResponseSchema(message="User account activated successfully.")


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Request a password reset token to be sent to the user's email.",
    responses={
        200: {
            "description": "Password reset token sent successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "If you are registered, "
                                   "you will receive an email with instructions."
                    }
                }
            }
        }
    },
)
async def request_password_reset_token(
    data: PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Request a password reset token to be sent to the user's email.

    Args:
        data: Email for which to request password reset.
        background_tasks: FastAPI background tasks for sending email.
        settings: Application settings.
        email_sender: Email sender service.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel | None = result.scalars().first()

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will receive an email with instructions."
        )

    if user:
        await db.execute(
            delete(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.user_id == user.id)
        )

    reset_token = PasswordResetTokenModel(user_id=user.id)
    db.add(reset_token)
    await db.commit()

    password_reset_link = f"{settings.BASE_URL}/password-reset/complete/?token={reset_token.token}"

    background_tasks.add_task(
        email_sender.send_password_reset_email,
        user.email,
        password_reset_link
    )

    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/password-reset/complete/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Complete password reset",
    description="Complete the password reset process using the token sent via email.",
    responses={
        200: {
            "description": "Password reset completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password reset successfully."
                    }
                }
            }
        },
        400: {
            "description": "Invalid email or token",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email or token."
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during password reset",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while resetting the password."
                    }
                }
            }
        }
    },
)
async def reset_password(
    data: PasswordResetCompleteRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Complete the password reset process using the token sent via email.

    Args:
        data: Email, new password, and reset token.
        background_tasks: FastAPI background tasks for sending email.
        settings: Application settings.
        email_sender: Email sender service.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel | None = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    stmt = (
        select(PasswordResetTokenModel)
        .where(PasswordResetTokenModel.user_id == user.id)
    )
    result = await db.execute(stmt)
    token_record: PasswordResetTokenModel | None = result.scalars().first()

    if not token_record or token_record.token != data.token or token_record.is_expired():
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    try:
        user.password = data.password
        await db.delete(token_record)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        )
    else:
        login_link = f"{settings.BASE_URL}/login/"

        background_tasks.add_task(
            email_sender.send_password_reset_complete_email,
            user.email,
            login_link
        )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/password-change/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change the user's password by providing the old and new password.",
    responses={
        200: {
            "description": "Password changed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password changed successfully."
                    }
                }
            }
        },
        400: {
            "description": "New password same as current password",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "New password must be different from the current password."
                    }
                }
            }
        },
        401: {
            "description": "Current password incorrect",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Current password is incorrect."
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during password change",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during password change."
                    }
                }
            }
        }
    },
)
async def change_password(
    data: PasswordChangeRequestSchema,
    background_tasks: BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Change the user's password by providing the old and new password.

    Args:
        data: Old and new password.
        background_tasks: FastAPI background tasks for sending email.
        user: The current authenticated user.
        email_sender: Email sender service.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    if not user.verify_password(data.old_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect."
        )

    if data.old_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password."
        )

    try:
        user.password = data.new_password

        stmt = (
            delete(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user.id)
        )
        await db.execute(stmt)

        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password change."
        )
    else:
        background_tasks.add_task(
            email_sender.send_password_changed_email,
            user.email
        )

    return MessageResponseSchema(message="Password changed successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and return JWT access and refresh tokens.",
    responses={
        200: {
            "description": "User successfully authenticated",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "is_active": True,
                            "created_at": "2024-01-01T00:00:00Z",
                            "group": {
                                "id": 1,
                                "name": "user"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email or password"
                    }
                }
            }
        },
        403: {
            "description": "Account not activated",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Account is not activated. "
                                  "Please check your email for activation link."
                    }
                }
            }
        }
    },
)
async def login_user(
    data: UserLoginRequestSchema,
    settings: BaseAppSettings = Depends(get_settings),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> UserLoginResponseSchema:
    """Authenticate user and return JWT access and refresh tokens.

    Args:
        data: Login credentials (email, password).
        settings: Application settings.
        jwt_manager: JWT manager service.
        db: Database session.

    Returns:
        UserLoginResponseSchema: JWT tokens for the user.
    """
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel | None = result.scalars().first()

    if not user or not user.verify_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated."
        )

    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        refresh_token = RefreshTokenModel.create(
            user_id=user.id,
            minutes_valid=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
            token=jwt_refresh_token
        )
        db.add(refresh_token)
        await db.flush()
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        )

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})

    return UserLoginResponseSchema(
        refresh_token=jwt_refresh_token,
        access_token=jwt_access_token
    )


@router.post(
    "/logout/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Logout user by deleting the refresh token.",
    responses={
        200: {
            "description": "User logged out successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully logged out."
                    }
                }
            }
        },
        401: {
            "description": "Invalid credentials or user not found/inactive",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_tokens": {
                            "summary": "Invalid Tokens",
                            "value": {"detail": "Invalid or mismatched tokens"}
                        },
                        "not_found": {
                            "summary": "User Not Found",
                            "value": {"detail": "User not found or inactive"}
                        }
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during logout",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during logout."
                    }
                }
            }
        }
    },
)
async def logout_user(
    data: TokenRefreshRequestSchema,
    access_token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Logout user by deleting the refresh token.

    Args:
        data: Refresh token to revoke.
        access_token: JWT access token.
        jwt_manager: JWT manager service.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    try:
        decoded_access_token = jwt_manager.decode_access_token(access_token)
        access_token_user_id = decoded_access_token.get("user_id")

        decoded_refresh_token = jwt_manager.decode_refresh_token(
            data.refresh_token
        )
        refresh_token_user_id = decoded_refresh_token.get("user_id")

        if access_token_user_id != refresh_token_user_id:
            raise BaseSecurityError
    except BaseSecurityError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or mismatched tokens"
        )

    stmt_user = (
        select(UserModel)
        .join(RefreshTokenModel)
        .where(UserModel.id == access_token_user_id)
    )
    result = await db.execute(stmt_user)
    user: UserModel | None = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    stmt_refresh_token = (
        select(RefreshTokenModel)
        .where(RefreshTokenModel.token == data.refresh_token)
    )
    result = await db.execute(stmt_refresh_token)
    refresh_token_record: RefreshTokenModel | None = result.scalars().first()

    if not refresh_token_record:
        return MessageResponseSchema(
            message="Successfully logged out."
        )

    try:
        await db.delete(refresh_token_record)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout."
        )

    return MessageResponseSchema(
        message="Successfully logged out."
    )


@router.post(
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Obtain a new access token using a valid refresh token.",
    responses={
        200: {
            "description": "Access token refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    }
                }
            }
        },
        400: {
            "description": "Invalid refresh token",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid refresh token"
                    }
                }
            }
        },
        401: {
            "description": "Refresh token not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Refresh token not found."
                    }
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found."
                    }
                }
            }
        }
    },
)
async def refresh_access_token(
    data: TokenRefreshRequestSchema,
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> TokenRefreshResponseSchema:
    """Obtain a new access token using a valid refresh token.

    Args:
        data: Refresh token.
        jwt_manager: JWT manager service.
        db: Database session.

    Returns:
        TokenRefreshResponseSchema: New access token.
    """
    try:
        decoded_token = jwt_manager.decode_refresh_token(data.refresh_token)
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    stmt = select(RefreshTokenModel).where(
        RefreshTokenModel.token == data.refresh_token
    )
    result = await db.execute(stmt)
    refresh_token_record: RefreshTokenModel | None = result.scalars().first()

    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found."
        )

    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    new_access_token = jwt_manager.create_access_token({"user_id": user_id})

    return TokenRefreshResponseSchema(access_token=new_access_token)


@router.post(
    "/verify/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Verify access token",
    description="Verify if a given access token is valid and not expired.",
    responses={
        200: {
            "description": "Token is valid",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Token valid."
                    }
                }
            }
        },
        401: {
            "description": "Token invalid or expired",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Token invalid or expired."
                    }
                }
            }
        }
    },
)
async def verify_access_token(
    data: TokenVerifyRequestSchema,
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Verify if a given access token is valid and not expired.

    Args:
        data: Access token to verify.
        jwt_manager: JWT manager service.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    try:
        decoded_token = jwt_manager.decode_access_token(data.access_token)
        user_id = decoded_token.get("user_id")

        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user: UserModel | None = result.scalars().first()

        if not user or not user.is_active:
            raise BaseSecurityError
    except BaseSecurityError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired."
        )

    return MessageResponseSchema(message="Token valid.")


@router.post(
    "/admin/users/{user_id}/change-group/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "accounts"],
    summary="Change user group (admin only)",
    description="Change the group (role) of a user. Only accessible by admins.",
    responses={
        200: {
            "description": "User group successfully changed",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User group successfully changed to admin"
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Admin access required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Admin privileges required."
                    }
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found"
                    }
                }
            }
        }
    }
)
async def change_user_group(
    user_id: int,
    data: UserGroupUpdateRequestSchema,
    authorized: None = Depends(admin_only),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Change the group (role) of a user. Only accessible by admins.

    Args:
        user_id: ID of the user to change group for.
        data: New group information.
        authorized: Dependency to ensure admin access.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    target_user: UserModel | None = result.scalars().first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    stmt = select(UserGroupModel).where(UserGroupModel.name == data.group_name)
    result = await db.execute(stmt)
    target_group: UserGroupModel | None = result.scalars().first()

    if not target_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group {data.group_name.value} not found."
        )

    if target_user.group_id == target_group.id:
        return MessageResponseSchema(
            message=f"User already has the {data.group_name.value} role."
        )

    try:
        target_user.group_id = target_group.id
        await db.commit()
        await db.refresh(target_user)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user's group."
        ) from e

    return MessageResponseSchema(
        message=f"User's group successfully changed to {data.group_name.value}."
    )


@router.post(
    "/admin/users/activate/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "accounts"],
    summary="Manually activate user (admin only)",
    description="Manually activate a user account. Only accessible by admins.",
    responses={
        200: {
            "description": "User activated successfully or already active",
            "content": {
                "application/json": {
                    "examples": {
                        "activated": {
                            "summary": "User Activated",
                            "value": {
                                "message": "User account for user@example.com "
                                           "has been manually activated."
                            }
                        },
                        "already_active": {
                            "summary": "Already Active",
                            "value": {
                                "message": "User account for user@example.com is already active."
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Admin access required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Admin privileges required."
                    }
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User with email user@example.com not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during activation",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to activate user account."
                    }
                }
            }
        }
    }
)
async def admin_activate_user(
    data: UserManualActivationSchema,
    background_tasks: BackgroundTasks,
    authorized: None = Depends(admin_only),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    settings: BaseAppSettings = Depends(get_settings),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Manually activate a user account. Only accessible by admins.

    Args:
        data: User email to activate.
        background_tasks: FastAPI background tasks for sending email.
        authorized: Dependency to ensure admin access.
        email_sender: Email sender service.
        settings: Application settings.
        db: Database session.

    Returns:
        MessageResponseSchema: Standard message response.
    """
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    target_user: UserModel | None = result.scalars().first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {data.email} not found."
        )

    if target_user.is_active:
        return MessageResponseSchema(
            message=f"User account for {data.email} is already active."
        )

    try:
        if target_user:
            await db.execute(
                delete(ActivationTokenModel)
                .where(ActivationTokenModel.user_id == target_user.id)
            )

        target_user.is_active = True
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user account."
        ) from e
    else:
        login_link = f"{settings.BASE_URL}/login/"

        background_tasks.add_task(
            email_sender.send_activation_complete_email,
            target_user.email,
            login_link
        )

    return MessageResponseSchema(
        message=f"User account for {data.email} has been manually activated."
    )
