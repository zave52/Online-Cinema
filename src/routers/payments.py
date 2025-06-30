from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import (
    RoleChecker,
    get_payment_service,
    get_current_user
)
from database import get_db
from database.models.accounts import UserGroupEnum, UserModel
from database.models.orders import OrderModel, OrderStatusEnum
from exceptions.payments import PaymentError
from payments.interfaces import PaymentServiceInterface
from schemas.payments import (
    PaymentIntentResponseSchema,
    CreatePaymentIntentSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.post(
    "/payments/create-intent/",
    response_model=PaymentIntentResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["payments"]
)
async def create_payment_intent(
    data: CreatePaymentIntentSchema,
    user: UserModel = Depends(get_current_user),
    payment_service: PaymentServiceInterface = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(OrderModel)
        .where(
            OrderModel.id == data.order_id,
            OrderModel.user_id == user.id
        )
    )
    result = await db.execute(stmt)
    order: OrderModel = result.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not on pending status."
        )

    total_amount = sum(item.price_at_order for item in order.items)

    if order.total_amount != total_amount:
        order.total_amount = total_amount
        await db.commit()

    try:
        intend_data = await payment_service.create_payment_intent(
            order=order,
            amount=order.total_amount
        )
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create payment intent: {str(e)}"
        )

    return PaymentIntentResponseSchema(
        id=intend_data["id"],
        client_secret=intend_data["client_secret"],
        amount=intend_data["amount"],
        currency=intend_data["currency"]
    )
