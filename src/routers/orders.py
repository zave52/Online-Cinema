from decimal import Decimal
from typing import Optional, Sequence

from fastapi import (
    APIRouter,
    status,
    Depends,
    HTTPException,
    Query,
    BackgroundTasks
)
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from config.dependencies import (
    get_current_user,
    RoleChecker,
    get_or_create_cart,
    get_payment_service,
    get_email_sender
)
from database import get_db
from database.models.accounts import UserModel, UserGroupEnum
from database.models.movies import MovieModel
from database.models.payments import PaymentModel, PaymentStatusEnum
from database.models.shopping_cart import CartModel, CartItemModel
from database.models.orders import OrderModel, OrderItemModel, OrderStatusEnum
from exceptions.payments import PaymentError
from notifications.interfaces import EmailSenderInterface
from payments.interfaces import PaymentServiceInterface
from schemas.orders import (
    OrderSchema,
    CreateOrderSchema,
    OrderListSchema,
    RefundRequestSchema,
    MessageResponseSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.post(
    "/orders/",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create order",
    description="Create a new order from cart items. "
                "Validates that movies are not already purchased and not in pending orders.",
    responses={
        201: {
            "description": "Order created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 1,
                        "status": "pending",
                        "total_amount": "29.97",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "items": [
                            {
                                "id": 1,
                                "order_id": 1,
                                "movie_id": 1,
                                "price_at_order": "9.99"
                            }
                        ]
                    }
                }
            }
        },
        400: {
            "description": "Cart is empty or invalid cart items",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cart is empty. Cannot create order."
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
        409: {
            "description": "Movies already purchased or in pending orders",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movies already purchased: The Shawshank Redemption"
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
                                "loc": ["body", "cart_item_ids"],
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
async def create_order(
    data: CreateOrderSchema,
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> OrderSchema:
    """Create a new order from cart items.

    Args:
        data (CreateOrderSchema): Order creation data with cart item IDs.
        user (UserModel): The current authenticated user.
        cart (CartModel): User's shopping cart.
        db (AsyncSession): Database session dependency.

    Returns:
        OrderSchema: The created order.
    """
    if not data.cart_item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty. Cannot create order."
        )

    cart_items_stmt = (
        select(CartItemModel)
        .options(joinedload(CartItemModel.movie))
        .where(
            CartItemModel.id.in_(data.cart_item_ids),
            CartItemModel.cart_id == cart.id
        )
    )
    result = await db.execute(cart_items_stmt)
    cart_items = result.scalars().all()

    if len(cart_items) != len(data.cart_item_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some cart items not found or don't belong to your cart."
        )

    purchased_movies = []
    available_movies = []

    for cart_item in cart_items:
        purchase_check_stmt = (
            select(MovieModel)
            .join(UserModel.purchased)
            .where(
                MovieModel.id == cart_item.movie_id,
                UserModel.id == user.id
            )
        )
        result = await db.execute(purchase_check_stmt)
        if result.scalars().first():
            purchased_movies.append(cart_item.movie.name)
        else:
            available_movies.append(cart_item)

    if purchased_movies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Movies already purchased: {', '.join(purchased_movies)}"
        )

    for cart_item in available_movies:
        pending_order_stmt = (
            select(OrderItemModel)
            .join(OrderModel)
            .where(
                OrderItemModel.movie_id == cart_item.movie_id,
                OrderModel.user_id == user.id,
                OrderModel.status == OrderStatusEnum.PENDING
            )
        )
        result = await db.execute(pending_order_stmt)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Movie '{cart_item.movie.name}' is already in a pending order."
            )

    total_amount = sum(item.movie.price for item in available_movies)

    order = OrderModel(
        user_id=user.id,
        status=OrderStatusEnum.PENDING,
        total_amount=Decimal(total_amount)
    )
    db.add(order)
    await db.flush()

    order_items = []
    for cart_item in available_movies:
        order_item = OrderItemModel(
            order_id=order.id,
            movie_id=cart_item.movie_id,
            price_at_order=cart_item.movie.price
        )
        order_items.append(order_item)
        db.add(order_item)

    for cart_item in available_movies:
        await db.delete(cart_item)

    await db.commit()

    order_query = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
        .where(OrderModel.id == order.id)
    )

    result = await db.execute(order_query)
    order_with_items = result.scalar_one()

    return OrderSchema.model_validate(order_with_items)


@router.get(
    "/orders/",
    response_model=OrderListSchema,
    status_code=status.HTTP_200_OK,
    summary="List user orders",
    description="Get a paginated list of orders for the current user with sorting options.",
    responses={
        200: {
            "description": "List of orders returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "orders": [
                            {
                                "id": 1,
                                "user_id": 1,
                                "status": "completed",
                                "total_amount": "29.97",
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z",
                                "items": [
                                    {
                                        "id": 1,
                                        "order_id": 1,
                                        "movie_id": 1,
                                        "price_at_order": "9.99"
                                    }
                                ]
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
async def get_user_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrderListSchema:
    """Get a paginated list of orders for the current user.

    Args:
        page (int): Page number for pagination.
        per_page (int): Number of orders per page.
        sort_by (Optional[str]): Field to sort by (e.g., 'created_at', 'total_amount').
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        OrderListSchema: Paginated list of user orders.
    """
    count_stmt = (
        select(func.count(OrderModel.id))
        .where(OrderModel.user_id == user.id)
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return OrderListSchema(orders=[], total_items=0, total_pages=0)

    order_stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
        .where(OrderModel.user_id == user.id)
    )

    if sort_by:
        sort_field = sort_by.strip("-")
        allowed_sort_fields = ("created_at", "total_amount", "status")
        if sort_field in allowed_sort_fields:
            column = getattr(OrderModel, sort_field)
            if sort_by.startswith("-"):
                order_stmt = order_stmt.order_by(desc(column))
            else:
                order_stmt = order_stmt.order_by(asc(column))
    else:
        order_stmt = order_stmt.order_by(desc(OrderModel.created_at))

    offset = (page - 1) * per_page

    order_stmt = order_stmt.offset(offset).limit(per_page)
    result = await db.execute(order_stmt)
    orders: Sequence[OrderModel] = result.scalars().all()

    order_list = [OrderSchema.model_validate(order) for order in orders]
    total_pages = (total_items + per_page - 1) // per_page

    return OrderListSchema(
        orders=order_list,
        prev_page=f"/ecommerce/orders/?page={page - 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page > 1 else None,
        next_page=f"/ecommerce/orders/?page={page + 1}&per_page={per_page}"
                  f"{f'&sort_by={sort_by}' if sort_by else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/orders/{order_id}/",
    response_model=OrderSchema,
    status_code=status.HTTP_200_OK,
    summary="Get order details",
    description="Retrieve detailed information about a specific order by its ID.",
    responses={
        200: {
            "description": "Order details returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 1,
                        "status": "completed",
                        "total_amount": "29.97",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "items": [
                            {
                                "id": 1,
                                "order_id": 1,
                                "movie_id": 1,
                                "price_at_order": "9.99"
                            },
                            {
                                "id": 2,
                                "order_id": 1,
                                "movie_id": 2,
                                "price_at_order": "9.99"
                            }
                        ]
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
                        "detail": "Order not found"
                    }
                }
            }
        }
    }
)
async def get_order_by_id(
    order_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrderSchema:
    """Retrieve detailed information about a specific order.

    Args:
        order_id (int): The ID of the order to retrieve.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        OrderSchema: Detailed order information.
    """
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
    order = result.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    order_data = {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "created_at": order.created_at,
        "total_amount": order.total_amount,
        "items": [
            {
                "id": item.id,
                "movie_id": item.movie_id,
                "price_at_order": item.price_at_order,
                "movie_name": item.movie.name
            }
            for item in order.items
        ]
    }

    return OrderSchema.model_validate(order_data)


@router.delete(
    "/orders/{order_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel order",
    description="Cancel a pending order. Paid orders cannot be canceled directly.",
    responses={
        204: {
            "description": "Order canceled successfully"
        },
        400: {
            "description": "Order cannot be canceled",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot cancel a completed order."
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
                        "detail": "Order not found"
                    }
                }
            }
        }
    }
)
async def cancel_order(
    order_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Cancel a pending order.

    Args:
        order_id (int): The ID of the order to cancel.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        None
    """
    stmt = (
        select(OrderModel)
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
            detail="Paid orders can only be canceled via refund request."
        )

    if order.status == OrderStatusEnum.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already canceled."
        )

    order.status = OrderStatusEnum.CANCELED
    await db.commit()
    await db.refresh(order)

    return


@router.post(
    "/orders/{order_id}/refund/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request refund",
    description="Request a refund for a paid order. "
                "Processes refund through payment service and removes movies from user's "
                "purchased list. Allowed refund reasons: 'requested_by_customer', "
                "'fraudulent', 'duplicate'.",
    responses={
        200: {
            "description": "Refund processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Refund processed successfully. Amount: $29.97"
                    }
                }
            }
        },
        400: {
            "description": "Order cannot be refunded",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order is not in a refundable state."
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
            "description": "Order or payment not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order or payment not found"
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
                                "loc": ["body", "reason"],
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
async def refund_order(
    order_id: int,
    data: RefundRequestSchema,
    background_tasks: BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    payment_service: PaymentServiceInterface = Depends(get_payment_service),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Request a refund for a paid order.

    Args:
        order_id (int): The ID of the order to refund.
        data (RefundRequestSchema): Refund request data.
        background_tasks (BackgroundTasks): FastAPI background tasks.
        user (UserModel): The current authenticated user.
        payment_service (PaymentServiceInterface): Payment service dependency.
        email_sender (EmailSenderInterface): Email sender dependency.
        db (AsyncSession): Database session dependency.

    Returns:
        MessageResponseSchema: Success message with refund information.
    """
    user_stmt = (
        select(UserModel)
        .options(selectinload(UserModel.purchased))
        .where(UserModel.id == user.id)
    )
    result = await db.execute(user_stmt)
    user_with_purchased = result.scalars().first()

    order_stmt = (
        select(OrderModel)
        .options(selectinload(OrderModel.payments))
        .where(
            OrderModel.id == order_id,
            OrderModel.user_id == user.id
        )
    )
    result = await db.execute(order_stmt)
    order = result.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not found."
        )

    if order.status != OrderStatusEnum.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paid orders can be refund."
        )

    payment_stmt = (
        select(PaymentModel)
        .where(
            PaymentModel.order_id == order_id,
            PaymentModel.status == PaymentStatusEnum.SUCCESSFUL
        )
    )
    result = await db.execute(payment_stmt)
    payment: PaymentModel = result.scalars().first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this order."
        )

    try:
        refund_data = await payment_service.process_refund(
            payment=payment,
            amount=data.amount,
            reason=data.reason
        )

        payment.status = PaymentStatusEnum.REFUNDED
        order.status = OrderStatusEnum.CANCELED

        order_items_stmt = (
            select(OrderItemModel)
            .where(OrderItemModel.order_id == order_id)
        )
        result = await db.execute(order_items_stmt)
        order_items = result.scalars().all()

        movie_ids_to_remove = {item.movie_id for item in order_items}
        user_with_purchased.purchased = [
            movie for movie in user_with_purchased.purchased
            if movie.id not in movie_ids_to_remove
        ]

        await db.commit()
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process refund: {str(e)}"
        )
    else:
        background_tasks.add_task(
            email_sender.send_refund_confirmation_email,
            user.email,
            order_id,
            refund_data.get("amount", data.amount)
        )

    return MessageResponseSchema(
        message=f"Refund processed successfully. Refund ID: {refund_data.get('id')}"
    )


@router.get(
    "/admin/orders/",
    response_model=OrderListSchema,
    status_code=status.HTTP_200_OK,
    tags=["orders", "moderator"],
    summary="List all orders (Admin)",
    description="Get a paginated list of all orders with filtering options. "
                "Only moderators and admins can access.",
    responses={
        200: {
            "description": "List of orders returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "orders": [
                            {
                                "id": 1,
                                "user_id": 1,
                                "status": "completed",
                                "total_amount": "29.97",
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z",
                                "items": [
                                    {
                                        "id": 1,
                                        "order_id": 1,
                                        "movie_id": 1,
                                        "price_at_order": "9.99"
                                    }
                                ]
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
async def get_all_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    status_filter: Optional[OrderStatusEnum] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> OrderListSchema:
    """Get a paginated list of all orders with filtering options.

    Args:
        page (int): Page number for pagination.
        per_page (int): Number of orders per page.
        user_id (Optional[int]): Filter by specific user ID.
        status_filter (Optional[OrderStatusEnum]): Filter by order status.
        date_from (Optional[str]): Filter orders from this date.
        date_to (Optional[str]): Filter orders to this date.
        authorized: Dependency to check moderator/admin rights.
        db (AsyncSession): Database session dependency.

    Returns:
        OrderListSchema: Paginated list of orders with filtering applied.
    """
    filters = []

    if user_id:
        filters.append(OrderModel.user_id == user_id)
    if status_filter:
        filters.append(OrderModel.status == status_filter)
    if date_from:
        filters.append(OrderModel.created_at >= date_from)
    if date_to:
        filters.append(OrderModel.created_at <= date_to)

    count_stmt = select(func.count(OrderModel.id.distinct())).where(
        *filters
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return OrderListSchema(orders=[], total_items=0, total_pages=0)

    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.items)
            .selectinload(OrderItemModel.movie),
            selectinload(OrderModel.user)
        )
    )

    if user_id:
        stmt = stmt.where(OrderModel.user_id == user_id)
    if status_filter:
        stmt = stmt.where(OrderModel.status == status_filter)
    if date_from:
        stmt = stmt.where(OrderModel.created_at >= date_from)
    if date_to:
        stmt = stmt.where(OrderModel.created_at <= date_to)

    stmt = stmt.order_by(desc(OrderModel.created_at))
    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    orders: Sequence[OrderModel] = result.scalars().all()

    order_list = [OrderSchema.model_validate(order) for order in orders]
    total_pages = (total_items + per_page - 1) // per_page

    return OrderListSchema(
        orders=order_list,
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
