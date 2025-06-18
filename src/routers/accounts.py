from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_email_sender
from database import get_db
from database.models.accounts import (
    UserModel,
    UserGroupModel,
    ActivationTokenModel,
    UserGroupEnum
)
from notifications.interfaces import EmailSenderInterface

from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema
)

router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def register_user(
    data: UserRegistrationRequestSchema,
    background_tasks: BackgroundTasks,
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {data.email} already exists."
        )

    stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
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
        activation_link = "http://localhost/api/v1/accounts/activate"

        background_tasks.add_task(
            email_sender.send_activation_email,
            new_user.email,
            activation_link
        )

    return UserRegistrationResponseSchema.model_validate(new_user)
