from typing import cast

from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import (
    get_s3_storage,
    get_current_user
)
from database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    GenderEnum
)
from database.models.profiles import UserProfileModel
from exceptions.storages import S3FileUploadError
from schemas.profiles import (
    ProfileResponseSchema,
    ProfileCreateRequestSchema,
    ProfileRetrieveSchema,
    ProfileUpdateRequestSchema,
    ProfilePatchRequestSchema
)
from database import get_db
from storages.interfaces import S3StorageInterface

router = APIRouter()


@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def create_profile(
    user_id: int,
    profile_data: ProfileCreateRequestSchema = Depends(
        ProfileCreateRequestSchema.from_form
    ),
    user: UserModel = Depends(get_current_user),
    s3_storage: S3StorageInterface = Depends(get_s3_storage),
    db: AsyncSession = Depends(get_db)
) -> ProfileResponseSchema:
    if user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile."
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
        gender=cast(GenderEnum, profile_data.gender.upper()),
        date_of_birth=profile_data.date_of_birth,
        info=profile_data.info,
        avatar=avatar_key
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    avatar_url = await s3_storage.get_file_url(new_profile.avatar)

    return ProfileResponseSchema(
        id=new_profile.id,
        user_id=new_profile.user_id,
        first_name=new_profile.first_name,
        last_name=new_profile.last_name,
        gender=str(new_profile.gender),
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
    current_user: UserModel = Depends(get_current_user),
    s3_storage: S3StorageInterface = Depends(get_s3_storage),
    db: AsyncSession = Depends(get_db)
) -> ProfileRetrieveSchema:
    if current_user.id != user_id:
        stmt = (
            select(UserGroupModel)
            .join(UserModel)
            .where(UserModel.id == current_user.id)
        )
        result = await db.execute(stmt)
        user_group: UserGroupModel = result.scalars().first()

        if not user_group or user_group.name != UserGroupEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this profile."
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


@router.put(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_200_OK
)
async def update_profile(
    user_id: int,
    profile_data: ProfileUpdateRequestSchema = Depends(
        ProfileUpdateRequestSchema.from_form
    ),
    current_user: UserModel = Depends(get_current_user),
    s3_storage: S3StorageInterface = Depends(get_s3_storage),
    db: AsyncSession = Depends(get_db)
) -> ProfileResponseSchema:
    if user_id != current_user.id:
        stmt = (
            select(UserGroupModel)
            .join(UserModel)
            .where(UserModel.id == current_user.id)
        )
        result = await db.execute(stmt)
        user_group: UserGroupModel = result.scalars().first()

        if not user_group or user_group.name != UserGroupEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this profile."
            )

    stmt = (
        select(UserProfileModel)
        .where(UserProfileModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    profile: UserProfileModel = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile for this user not found."
        )

    profile.first_name = profile_data.first_name
    profile.last_name = profile_data.last_name
    profile.gender = cast(GenderEnum, profile_data.gender.upper())
    profile.date_of_birth = profile_data.date_of_birth
    profile.info = profile_data.info

    if profile_data.avatar:
        avatar_bytes = await profile_data.avatar.read()
        avatar_key = f"avatars/{user_id}_{profile_data.avatar.filename}"

        try:
            await s3_storage.upload_file(
                file_name=avatar_key,
                file_data=avatar_bytes
            )
            profile.avatar = avatar_key
        except S3FileUploadError as e:
            print(f"Error uploading avatar to S3: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload avatar. Please try again later."
            )

    await db.commit()
    await db.refresh(profile)

    avatar_url = await s3_storage.get_file_url(profile.avatar)

    return ProfileResponseSchema(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=str(profile.gender),
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar=cast(HttpUrl, avatar_url)
    )


@router.patch(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_200_OK
)
async def patch_profile(
    user_id: int,
    profile_data: ProfilePatchRequestSchema = Depends(
        ProfilePatchRequestSchema.from_form
    ),
    current_user: UserModel = Depends(get_current_user),
    s3_storage: S3StorageInterface = Depends(get_s3_storage),
    db: AsyncSession = Depends(get_db)
) -> ProfileResponseSchema:
    if user_id != current_user.id:
        stmt = (
            select(UserGroupModel)
            .join(UserModel)
            .where(UserModel.id == current_user.id)
        )
        result = await db.execute(stmt)
        user_group: UserGroupModel = result.scalars().first()

        if not user_group or user_group.name != UserGroupEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this profile."
            )

    stmt = (
        select(UserProfileModel)
        .where(UserProfileModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    profile: UserProfileModel = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile for this user not found."
        )

    if profile_data.first_name is not None:
        profile.first_name = profile_data.first_name

    if profile_data.last_name is not None:
        profile.last_name = profile_data.last_name

    if profile_data.gender is not None:
        profile.gender = cast(GenderEnum, profile_data.gender.upper())

    if profile_data.date_of_birth is not None:
        profile.date_of_birth = profile_data.date_of_birth

    if profile_data.info is not None:
        profile.info = profile_data.info

    if profile_data.avatar:
        avatar_bytes = await profile_data.avatar.read()
        avatar_key = f"avatars/{user_id}_{profile_data.avatar.filename}"

        try:
            await s3_storage.upload_file(
                file_name=avatar_key,
                file_data=avatar_bytes
            )
            profile.avatar = avatar_key
        except S3FileUploadError as e:
            print(f"Error uploading avatar to S3: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload avatar. Please try again later."
            )

    await db.commit()
    await db.refresh(profile)

    avatar_url = await s3_storage.get_file_url(profile.avatar)

    return ProfileResponseSchema(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=str(profile.gender),
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar=cast(HttpUrl, avatar_url)
    )
