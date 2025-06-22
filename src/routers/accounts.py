from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.dependencies import (
    get_email_sender,
    get_jwt_manager,
    get_settings,
    get_token
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


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def register_user(
    data: UserRegistrationRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
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
        activation_link = f"{settings.BASE_URL}/activate/"

        background_tasks.add_task(
            email_sender.send_activation_email,
            new_user.email,
            activation_link
        )

    return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/activate/resend/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def resend_activation_token(
    data: ResendActivationTokenRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    standard_response = MessageResponseSchema(
        message="If your account exists and is not activated, you will receive an email with instructions."
    )

    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user: UserModel = result.scalars().first()

    if not user or user.is_active:
        return standard_response

    stmt = (
        delete(ActivationTokenModel)
        .where(ActivationTokenModel.id == user.id)
    )

    try:
        await db.execute(stmt)

        new_activation_token = ActivationTokenModel(user_id=user.id)
        db.add(new_activation_token)
        await db.commit()
        await db.refresh(new_activation_token)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during resending activation token."
        )
    else:
        activation_link = f"{settings.BASE_URL}/activate/"

        background_tasks.add_task(
            email_sender.send_activation_email,
            user.email,
            activation_link
        )

    return standard_response


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def activate_account(
    data: UserActivationRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
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
    status_code=status.HTTP_200_OK
)
async def request_password_reset_token(
    data: PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    settings: BaseAppSettings = Depends(get_settings),
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

    password_reset_link = f"{settings.BASE_URL}/password-reset/complete/"

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
    settings: BaseAppSettings = Depends(get_settings),
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
        login_link = f"{settings.BASE_URL}/login/"

        background_tasks.add_task(
            email_sender.send_activation_complete_email,
            user.email,
            login_link
        )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/password-change/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def change_password(
    data: PasswordChangeRequestSchema,
    background_tasks: BackgroundTasks,
    token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    try:
        decoded_token = jwt_manager.decode_access_token(token)
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user: UserModel = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive."
        )

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
            .where(RefreshTokenModel.user_id == user_id)
        )
        await db.execute(stmt)

        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError as e:
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
    "/logout/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def logout_user(
    data: TokenRefreshRequestSchema,
    access_token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
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
    user: UserModel = result.scalars().first()

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
    refresh_token_record: RefreshTokenModel = result.scalars().first()

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


@router.post(
    "/admin/users/{user_id}/change-group/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin"]
)
async def change_user_group(
    user_id: int,
    data: UserGroupUpdateRequestSchema,
    token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    try:
        decoded_token = jwt_manager.decode_access_token(token)
        admin_user_id = decoded_token.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    stmt = (
        select(UserGroupModel)
        .join(UserModel)
        .where(UserModel.id == admin_user_id)
    )
    result = await db.execute(stmt)
    admin_group: UserGroupModel = result.scalars().first()

    if not admin_group or admin_group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change user groups."
        )

    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    target_user: UserModel = result.scalars().first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    stmt = select(UserGroupModel).where(UserGroupModel.name == data.group_name)
    result = await db.execute(stmt)
    target_group: UserGroupModel = result.scalars().first()

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
    tags=["admin"]
)
async def admin_activate_user(
    data: UserManualActivationSchema,
    background_tasks: BackgroundTasks,
    token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    settings: BaseAppSettings = Depends(get_settings),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    try:
        decoded_token = jwt_manager.decode_access_token(token)
        admin_user_id = decoded_token.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    stmt = (
        select(UserGroupModel)
        .join(UserModel)
        .where(UserModel.id == admin_user_id)
    )
    result = await db.execute(stmt)
    admin_group: UserGroupModel = result.scalars().first()

    if not admin_group or admin_group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manually activate users."
        )

    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    target_user: UserModel = result.scalars().first()

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
        stmt = (
            delete(ActivationTokenModel)
            .where(ActivationTokenModel.user_id == target_user.id)
        )
        await db.execute(stmt)

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
