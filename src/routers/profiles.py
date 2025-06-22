from typing import cast

from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_token, get_jwt_manager, get_s3_storage
from database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    GenderEnum
)
from database.models.profiles import UserProfileModel
from exceptions.security import BaseSecurityError
from exceptions.storages import S3FileUploadError
from schemas.profiles import (
    ProfileCreateResponseSchema,
    ProfileCreateRequestSchema,
    ProfileRetrieveSchema
)
from database import get_db
from security.interfaces import JWTManagerInterface
from storages.interfaces import S3StorageInterface

router = APIRouter()


@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileCreateResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def create_profile(
    user_id: int,
    profile_data: ProfileCreateRequestSchema = Depends(
        ProfileCreateRequestSchema.from_form
    ),
    token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    s3_storage: S3StorageInterface = Depends(get_s3_storage),
    db: AsyncSession = Depends(get_db)
) -> ProfileCreateResponseSchema:
    try:
        payload = jwt_manager.decode_access_token(token)
        token_user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    if user_id != token_user_id:
        stmt = (
            select(UserGroupModel)
            .join(UserModel)
            .where(UserModel.id == token_user_id)
        )
        result = await db.execute(stmt)
        user_group: UserGroupModel = result.scalars().first()

        if not user_group or not user_group.name == UserGroupEnum.USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this profile."
            )

    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user: UserModel = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or is not active."
        )

    stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    result = await db.execute(stmt)
    existing_profile = result.scalars().first()

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile."
        )

    avatar_bytes = await profile_data.avatar.read()
    avatar_key = f"avatars/{user_id}_{profile_data.avatar.filename}"

    try:
        await s3_storage.upload_file(
            file_name=avatar_key,
            file_data=avatar_bytes
        )
    except S3FileUploadError as e:
        print(f"Error uploading avatar to S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later."
        )

    new_profile = UserProfileModel(
        user_id=cast(int, user.id),
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        gender=cast(GenderEnum, profile_data.gender),
        date_of_birth=profile_data.date_of_birth,
        info=profile_data.info,
        avatar=avatar_key
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    avatar_url = await s3_storage.get_file_url(new_profile.avatar)

    return ProfileCreateResponseSchema(
        id=new_profile.id,
        user_id=new_profile.user_id,
        first_name=new_profile.first_name,
        last_name=new_profile.last_name,
        gender=cast(str, new_profile.gender),
        date_of_birth=new_profile.date_of_birth,
        info=new_profile.info,
        avatar=cast(HttpUrl, avatar_url)
    )


@router.get(
    "/users/{user_id}/profile/",
    response_model=ProfileRetrieveSchema,
    status_code=status.HTTP_200_OK
)
async def get_user_profile(
    user_id: int,
    token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    s3_storage: S3StorageInterface = Depends(get_s3_storage),
    db: AsyncSession = Depends(get_db)
) -> ProfileRetrieveSchema:
    try:
        decoded_token = jwt_manager.decode_access_token(token)
        token_user_id = decoded_token.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    if token_user_id != user_id:
        stmt = (
            select(UserGroupModel)
            .join(UserModel)
            .where(UserModel.id == token_user_id)
        )
        result = await db.execute(stmt)
        user_group: UserGroupModel = result.scalars().first()

        if not user_group or user_group.name != UserGroupEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this profile."
            )

    user_stmt = select(UserModel).where(UserModel.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or is not active."
        )

    stmt = (
        select(UserProfileModel)
        .join(UserModel)
        .where(UserModel.id == user_id)
    )
    result = await db.execute(stmt)
    user_profile: UserProfileModel = result.scalars().first()

    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile for this user not found."
        )

    avatar_url = await s3_storage.get_file_url(file_name=user_profile.avatar)

    return ProfileRetrieveSchema(
        id=user_profile.id,
        user_id=user_profile.user_id,
        email=cast(str, user_profile.user.email),
        first_name=user_profile.first_name,
        last_name=user_profile.last_name,
        gender=cast(str, user_profile.gender),
        info=user_profile.info,
        date_of_birth=user_profile.date_of_birth,
        avatar=cast(HttpUrl, avatar_url)
    )
