from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.background import BackgroundTasks

from config.dependencies import (
    RoleChecker,
    get_payment_service,
    get_current_user,
    get_email_sender
)
from database import get_db
from database.models.accounts import UserGroupEnum, UserModel
from database.models.orders import OrderModel, OrderStatusEnum, OrderItemModel
from database.models.payments import PaymentItemModel
from exceptions.payments import PaymentError
from notifications.interfaces import EmailSenderInterface
from payments.interfaces import PaymentServiceInterface
from schemas.payments import (
    PaymentIntentResponseSchema,
    CreatePaymentIntentSchema,
    MessageResponseSchema,
    ProcessPaymentSchema
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


@router.post(
    "/payments/process/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["payments"]
)
async def process_payment(
    data: ProcessPaymentSchema,
    background_tasks: BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    payment_service: PaymentServiceInterface = Depends(get_payment_service),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    try:
        intent_data = await payment_service.retrieve_payment_intent(
            data.payment_intent_id
        )
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment intent: {str(e)}"
        )

    order_id = int(intent_data["metadata"]["order_id"])

    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
        .where(
            OrderModel.id == order_id,
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

    expected_amount = sum(item.price_at_order for item in order.items)
    actual_amount = intent_data["amount"]

    if expected_amount != actual_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount does not match order total."
        )

    try:
        payment = await payment_service.process_payment(
            payment_intent_id=data.payment_intent_id,
            order=order,
            user_id=user.id
        )

        db.add(payment)
        await db.refresh(payment)

        for order_item in order.items:
            payment_item = PaymentItemModel(
                price_at_payment=order_item.price_at_order,
                payment_id=payment.id,
                order_item_id=order_item.id
            )
            db.add(payment_item)

        order.status = OrderStatusEnum.PAID

        for order_item in order.items:
            user.purchased.append(order_item.movie)

        await db.commit()
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process payment: {str(e)}"
        )
    else:
        background_tasks.add_task(
            email_sender.send_payment_confirmation_email,
            user.email,
            order.id,
            payment.amount
        )

    return MessageResponseSchema(
        message=f"Payment processed successfully. Payment ID: {payment.id}"
    )
