from decimal import Decimal
from typing import Optional, Sequence

from fastapi import APIRouter, status, Depends, HTTPException, Query, Request
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
from database.models.payments import (
    PaymentItemModel,
    PaymentModel,
    PaymentStatusEnum
)
from exceptions.payments import PaymentError, WebhookError
from notifications.interfaces import EmailSenderInterface
from payments.interfaces import PaymentServiceInterface
from schemas.payments import (
    PaymentIntentResponseSchema,
    CreatePaymentIntentSchema,
    MessageResponseSchema,
    ProcessPaymentRequestSchema,
    PaymentListSchema,
    PaymentSchema,
    CheckoutSessionRequestSchema,
    CheckoutSessionResponseSchema, ProcessPaymentResponseSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.post(
    "/payments/create-intent/",
    response_model=PaymentIntentResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Create payment intent",
    description="Create a payment intent for a pending order. "
                "This is the first step in the payment process.",
    responses={
        200: {
            "description": "Payment intent created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "pi_1234567890abcdef",
                        "client_secret": "pi_1234567890abcdef_secret_abcdef1234567890",
                        "amount": "2997",
                        "currency": "usd"
                    }
                }
            }
        },
        400: {
            "description": "Order is not in pending status or payment service error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order is not on pending status."
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        404: {
            "description": "Order not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order not found."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "order_id"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_payment_intent(
    data: CreatePaymentIntentSchema,
    user: UserModel = Depends(get_current_user),
    payment_service: PaymentServiceInterface = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db)
) -> PaymentIntentResponseSchema:
    """Create a payment intent for a pending order.

    Args:
        data (CreatePaymentIntentSchema): Payment intent creation data.
        user (UserModel): The current authenticated user.
        payment_service (PaymentServiceInterface): Payment service dependency.
        db (AsyncSession): Database session dependency.

    Returns:
        PaymentIntentResponseSchema: Payment intent details for client-side processing.
    """
    stmt = (
        select(OrderModel)
        .options(selectinload(OrderModel.items))
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
            amount=Decimal(order.total_amount)
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
    response_model=ProcessPaymentResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Process payment",
    description="Process a payment using a payment intent. "
                "Updates order status and adds movies to user's purchased list.",
    responses={
        200: {
            "description": "Payment processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "payment_id": 1
                    }
                }
            }
        },
        400: {
            "description": "Payment processing failed or order already paid",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "This order has already been paid for."
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        404: {
            "description": "Order not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order not found."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "payment_intent_id"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def process_payment(
    data: ProcessPaymentRequestSchema,
    background_tasks: BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    payment_service: PaymentServiceInterface = Depends(get_payment_service),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> ProcessPaymentResponseSchema:
    """Process a payment using a payment intent.

    Args:
        data (ProcessPaymentRequestSchema): Payment processing data.
        background_tasks (BackgroundTasks): FastAPI background tasks.
        user (UserModel): The current authenticated user.
        payment_service (PaymentServiceInterface): Payment service dependency.
        email_sender (EmailSenderInterface): Email sender dependency.
        db (AsyncSession): Database session dependency.

    Returns:
        ProcessPaymentResponseSchema: payment id.
    """
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

    if order.status == OrderStatusEnum.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order has already been paid for."
        )

    expected_amount = sum(Decimal(item.price_at_order) for item in order.items)
    actual_amount = Decimal(intent_data["amount"]).quantize(Decimal('0.01'))

    if expected_amount != actual_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount does not match order total. "
                   f"Expected: {expected_amount}, Actual: {actual_amount}"
        )

    try:
        payment = await payment_service.process_payment(
            payment_intent_id=data.payment_intent_id,
            order=order,
            user_id=user.id
        )

        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        for order_item in order.items:
            payment_item = PaymentItemModel(
                price_at_payment=order_item.price_at_order,
                payment_id=payment.id,
                order_item_id=order_item.id
            )
            db.add(payment_item)

        order.status = OrderStatusEnum.PAID

        await db.refresh(user, attribute_names=["purchased"])
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

    return ProcessPaymentResponseSchema(payment_id=payment.id)


@router.get(
    "/payments/",
    response_model=PaymentListSchema,
    status_code=status.HTTP_200_OK,
    summary="List user payments",
    description="Get a paginated list of payments for the current user with sorting options.",
    responses={
        200: {
            "description": "List of payments returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "payments": [
                            {
                                "id": 1,
                                "user_id": 1,
                                "order_id": 1,
                                "payment_intent_id": "pi_1234567890abcdef",
                                "amount": "29.97",
                                "currency": "usd",
                                "status": "succeeded",
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z"
                            }
                        ],
                        "total_pages": 1,
                        "total_items": 1,
                        "prev_page": None,
                        "next_page": None
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "page"],
                                "msg": "ensure this value is greater than or equal to 1",
                                "type": "value_error.number.not_ge"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_user_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaymentListSchema:
    """Get a paginated list of payments for the current user.

    Args:
        page (int): Page number for pagination.
        per_page (int): Number of payments per page.
        sort_by (Optional[str]): Field to sort by (e.g., 'created_at', 'amount').
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        PaymentListSchema: Paginated list of user payments.
    """
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
    payments: Sequence[PaymentModel] = result.scalars().all()

    payment_list = [
        PaymentSchema.model_validate(payment) for payment in payments
    ]
    total_pages = (total_items + per_page - 1) // per_page

    return PaymentListSchema(
        payments=payment_list,
        prev_page=f"/ecommerce/payments/?page={page - 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page > 1 else None,
        next_page=f"/ecommerce/payments/?page={page + 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/payments/{payment_id}/",
    response_model=PaymentSchema,
    status_code=status.HTTP_200_OK,
    summary="Get payment details",
    description="Retrieve detailed information about a specific payment by its ID.",
    responses={
        200: {
            "description": "Payment details returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 1,
                        "order_id": 1,
                        "payment_intent_id": "pi_1234567890abcdef",
                        "amount": "29.97",
                        "currency": "usd",
                        "status": "succeeded",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        404: {
            "description": "Payment not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Payment not found"
                    }
                }
            }
        }
    }
)
async def get_payment_by_id(
    payment_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaymentSchema:
    """Retrieve detailed information about a specific payment.

    Args:
        payment_id (int): The ID of the payment to retrieve.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        PaymentSchema: Detailed payment information.
    """
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


@router.post(
    "/payments/checkout-session/",
    response_model=CheckoutSessionResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Create checkout session",
    description="Create a checkout session for a pending order. "
                "Used for redirect-based payment flows.",
    responses={
        200: {
            "description": "Checkout session created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "cs_1234567890abcdef",
                        "url": "https://checkout.stripe.com/pay/cs_1234567890abcdef"
                    }
                }
            }
        },
        400: {
            "description": "Order is not in pending status or payment service error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order is not on pending status."
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        404: {
            "description": "Order not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order not found."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "order_id"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_checkout_session(
    data: CheckoutSessionRequestSchema,
    user: UserModel = Depends(get_current_user),
    payment_service: PaymentServiceInterface = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db)
) -> CheckoutSessionResponseSchema:
    """Create a checkout session for a pending order.

    Args:
        data (CheckoutSessionRequestSchema): Checkout session creation data.
        user (UserModel): The current authenticated user.
        payment_service (PaymentServiceInterface): Payment service dependency.
        db (AsyncSession): Database session dependency.

    Returns:
        CheckoutSessionResponseSchema: Checkout session details for redirect.
    """
    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.items)
            .selectinload(OrderItemModel.movie)
        )
        .where(
            OrderModel.id == data.order_id,
            OrderModel.user_id == user.id
        )
    )
    result = await db.execute(stmt)
    order = result.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not in pending status."
        )

    try:
        session_data = await payment_service.create_checkout_session(
            order=order,
            success_url=data.success_url,
            cancel_url=data.cancel_url
        )
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create checkout session: {str(e)}"
        )

    return CheckoutSessionResponseSchema(
        id=session_data["id"],
        url=session_data["url"],
        amount_total=session_data["amount_total"]
    )


@router.post(
    "/payments/webhook/",
    status_code=status.HTTP_200_OK,
    summary="Handle payment webhook",
    description="Handle incoming webhooks from payment service (e.g., Stripe). "
                "Processes payment status updates.",
    responses={
        200: {
            "description": "Webhook processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Webhook processed successfully"
                    }
                }
            }
        },
        400: {
            "description": "Webhook processing failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid webhook signature"
                    }
                }
            }
        }
    }
)
async def handle_webhook(
    request: Request,
    payment_service: PaymentServiceInterface = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_email_sender)
) -> dict:
    """Handle incoming webhooks from payment service.

    Args:
        request (Request): The incoming webhook request.
        payment_service (PaymentServiceInterface): Payment service dependency.
        db (AsyncSession): Database session dependency.
        email_sender (EmailSenderInterface): Email sender dependency.

    Returns:
        dict: Webhook processing result.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        result = await payment_service.handle_webhook(
            payload,
            signature,
            db,
            email_sender
        )
        return result
    except WebhookError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get(
    "/admin/payments/",
    response_model=PaymentListSchema,
    status_code=status.HTTP_200_OK,
    tags=["payments", "moderator"],
    summary="List all payments (Admin)",
    description="Get a paginated list of all payments with filtering options. "
                "Only moderators and admins can access.",
    responses={
        200: {
            "description": "List of payments returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "payments": [
                            {
                                "id": 1,
                                "user_id": 1,
                                "order_id": 1,
                                "payment_intent_id": "pi_1234567890abcdef",
                                "amount": "29.97",
                                "currency": "usd",
                                "status": "succeeded",
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z"
                            }
                        ],
                        "total_pages": 1,
                        "total_items": 1,
                        "prev_page": None,
                        "next_page": None
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "page"],
                                "msg": "ensure this value is greater than or equal to 1",
                                "type": "value_error.number.not_ge"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_all_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    status_filter: Optional[PaymentStatusEnum] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> PaymentListSchema:
    """Get a paginated list of all payments with filtering options.

    Args:
        page (int): Page number for pagination.
        per_page (int): Number of payments per page.
        user_id (Optional[int]): Filter by specific user ID.
        status_filter (Optional[PaymentStatusEnum]): Filter by payment status.
        date_from (Optional[str]): Filter payments from this date.
        date_to (Optional[str]): Filter payments to this date.
        authorized: Dependency to check moderator/admin rights.
        db (AsyncSession): Database session dependency.

    Returns:
        PaymentListSchema: Paginated list of payments with filtering applied.
    """
    filters = []

    stmt = (
        select(PaymentModel)
        .options(
            selectinload(PaymentModel.items)
            .selectinload(PaymentItemModel.order_item),
            selectinload(PaymentModel.user)
        )
    )

    if user_id:
        fltr = PaymentModel.user_id == user_id
        stmt = stmt.where(fltr)
        filters.append(fltr)
    if status_filter:
        fltr = PaymentModel.status == status_filter
        stmt = stmt.where(fltr)
        filters.append(fltr)
    if date_from:
        fltr = PaymentModel.created_at >= date_from
        stmt = stmt.where(fltr)
        filters.append(fltr)
    if date_to:
        fltr = PaymentModel.created_at <= date_to
        stmt = stmt.where(fltr)
        filters.append(fltr)

    count_stmt = (
        select(func.count(PaymentModel.id.distinct()))
        .where(*filters)
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return PaymentListSchema(payments=[], total_pages=0, total_items=0)

    stmt = stmt.order_by(desc(PaymentModel.created_at))
    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    payments: Sequence[PaymentModel] = result.scalars().all()

    payment_list = [
        PaymentSchema.model_validate(payment) for payment in payments
    ]
    total_pages = (total_items + per_page - 1) // per_page

    return PaymentListSchema(
        payments=payment_list,
        prev_page=f"/ecommerce/admin/orders/?page={page - 1}&per_page={per_page}"
                  f"{f'&user_id={user_id}' if user_id else ''}"
                  f"{f'&status_filter={status_filter}' if status_filter else ''}"
                  f"{f'&date_from={date_from}' if date_from else ''}"
                  f"{f'&date_to={date_to}' if date_to else ''}" if page > 1 else None,
        next_page=f"/ecommerce/admin/orders/?page={page + 1}&per_page={per_page}"
                  f"{f'&user_id={user_id}' if user_id else ''}"
                  f"{f'&status_filter={status_filter}' if status_filter else ''}"
                  f"{f'&date_from={date_from}' if date_from else ''}"
                  f"{f'&date_to={date_to}' if date_to else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )
