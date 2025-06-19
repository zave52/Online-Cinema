from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.dependencies import (
    get_email_sender,
    get_base_url,
    get_jwt_manager,
    get_settings
)
from config.settings import BaseAppSettings
from database import get_db
from database.models.accounts import (
    UserModel,
    UserGroupModel,
    ActivationTokenModel,
    UserGroupEnum,
    PasswordResetTokenModel, RefreshTokenModel
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
    TokenRefreshRequestSchema, TokenVerifyRequestSchema
)
from security.interfaces import JWTManagerInterface

router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def register_user(
    data: UserRegistrationRequestSchema,
    background_tasks: BackgroundTasks,
    base_url: str = Depends(get_base_url),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> UserRegistrationResponseSchema:
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
        activation_link = f"{base_url}/activate/"

        background_tasks.add_task(
            email_sender.send_activation_email,
            new_user.email,
            activation_link
        )

    return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def activate_account(
    data: UserActivationRequestSchema,
    background_tasks: BackgroundTasks,
    base_url: str = Depends(get_base_url),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .join(UserModel).where(
            ActivationTokenModel.token == data.token,
            UserModel.email == data.email
        )
    )
    result = await db.execute(stmt)
    token_record: ActivationTokenModel = result.scalars().first()

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

    login_link = f"{base_url}/login/"

    background_tasks.add_task(
        email_sender.send_activation_complete_email,
        user.email,
        login_link
    )

    return MessageResponseSchema(message="User account activated successfully.")


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def request_password_reset_token(
    data: PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    base_url: str = Depends(get_base_url),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel = result.scalars().first()

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will receive an email with instructions."
        )

    stmt = (
        delete(PasswordResetTokenModel)
        .where(PasswordResetTokenModel.user_id == user.id)
    )
    await db.execute(stmt)

    reset_token = PasswordResetTokenModel(user_id=user.id)
    db.add(reset_token)
    await db.commit()

    password_reset_link = f"{base_url}/password-reset/complete/"

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
    status_code=status.HTTP_200_OK
)
async def reset_password(
    data: PasswordResetCompleteRequestSchema,
    background_tasks: BackgroundTasks,
    base_url: str = Depends(get_base_url),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel = result.scalars().first()

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
    token_record: PasswordResetTokenModel = result.scalars().first()

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
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        )
    else:
        login_link = f"{base_url}/login/"

        background_tasks.add_task(
            email_sender.send_activation_complete_email,
            user.email,
            login_link
        )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    status_code=status.HTTP_200_OK
)
async def login_user(
    data: UserLoginRequestSchema,
    settings: BaseAppSettings = Depends(get_settings),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> UserLoginResponseSchema:
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel = result.scalars().first()

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
    except SQLAlchemyError as e:
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
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    status_code=status.HTTP_200_OK
)
async def refresh_access_token(
    data: TokenRefreshRequestSchema,
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> TokenRefreshResponseSchema:
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
    refresh_token_record: RefreshTokenModel = result.scalars().first()

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
    status_code=status.HTTP_200_OK
)
async def verify_access_token(
    data: TokenVerifyRequestSchema,
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    try:
        decoded_token = jwt_manager.decode_access_token(data.access_token)
        user_id = decoded_token.get("user_id")

        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user: UserModel = result.scalars().first()

        if not user or not user.is_active:
            raise BaseSecurityError
    except BaseSecurityError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired."
        )

    return MessageResponseSchema(message="Token valid.")
