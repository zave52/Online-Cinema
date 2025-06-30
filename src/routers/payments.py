from typing import Optional, Sequence

from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy import select, func, asc, desc
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
from database.models.payments import PaymentItemModel, PaymentModel
from exceptions.payments import PaymentError
from notifications.interfaces import EmailSenderInterface
from payments.interfaces import PaymentServiceInterface
from schemas.payments import (
    PaymentIntentResponseSchema,
    CreatePaymentIntentSchema,
    MessageResponseSchema,
    ProcessPaymentSchema,
    PaymentListSchema,
    PaymentSchema
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


@router.get(
    "/payments/",
    response_model=PaymentListSchema,
    status_code=status.HTTP_200_OK,
    tags=["payments"]
)
async def get_user_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaymentListSchema:
    count_stmt = (
        select(func.count(PaymentModel.id))
        .where(PaymentModel.user_id == user.id)
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return PaymentListSchema(payments=[], total_items=0, total_pages=0)

    stmt = (
        select(PaymentModel)
        .options(
            selectinload(PaymentModel.items)
            .selectinload(PaymentItemModel.order_item)
        )
        .where(PaymentModel.user_id == user.id)
    )

    if sort_by:
        sort_field = sort_by.strip("-")
        allowed_sort_fields = ("created_at", "amount", "status")
        if sort_field in allowed_sort_fields:
            column = getattr(PaymentModel, sort_field)
            if sort_by.startswith("-"):
                stmt = stmt.order_by(desc(column))
            else:
                stmt = stmt.order_by(asc(column))
    else:
        stmt = stmt.order_by(desc(PaymentModel.created_at))

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    payments = Sequence[PaymentModel] = result.scalars().all()

    payment_list = [
        PaymentSchema.model_validate(payment) for payment in payments
    ]
    total_pages = (total_items + per_page - 1) // per_page

    return PaymentListSchema(
        payments=payment_list,
        prev_page=f"/ecommerce/payments/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/ecommerce/payments/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/payments/{payment_id}/",
    response_model=PaymentSchema,
    status_code=status.HTTP_200_OK,
    tags=["payments"]
)
async def get_payment_by_id(
    payment_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaymentSchema:
    stmt = (
        select(PaymentModel)
        .options(
            selectinload(PaymentModel.items)
            .selectinload(PaymentItemModel.order_item)
        )
        .where(
            PaymentModel.id == payment_id,
            PaymentModel.user_id == user.id
        )
    )
    result = await db.execute(stmt)
    payment = result.scalars().first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found."
        )

    return PaymentSchema.model_validate(payment)
