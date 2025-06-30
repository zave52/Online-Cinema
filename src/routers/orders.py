from typing import Optional

from fastapi import (
    APIRouter,
    status,
    Depends,
    HTTPException,
    Query
)
from mypy.applytype import Sequence
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from config.dependencies import (
    get_current_user,
    RoleChecker,
    get_or_create_cart
)
from database import get_db
from database.models.accounts import UserModel, UserGroupEnum
from database.models.movies import MovieModel
from database.models.shopping_cart import CartModel, CartItemModel
from database.models.orders import OrderModel, OrderItemModel, OrderStatusEnum
from schemas.orders import (
    OrderSchema,
    CreateOrderSchema,
    OrderListSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.post(
    "/orders/",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["orders"]
)
async def create_order(
    data: CreateOrderSchema,
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> OrderSchema:
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
        total_amount=total_amount
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
    await db.refresh(order)

    return OrderSchema.model_validate(order)


@router.get(
    "/orders/",
    response_model=OrderListSchema,
    status_code=status.HTTP_200_OK,
    tags=["orders"]
)
async def get_user_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrderListSchema:
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
        sorf_field = sort_by.strip("-")
        allowed_sort_fields = ("created_at", "total_amount", "status")
        if sorf_field in allowed_sort_fields:
            column = getattr(OrderModel, sorf_field)
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
        prev_page=f"/ecommerce/orders/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/ecommerce/orders/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/orders/{order_id}/",
    response_model=OrderSchema,
    status_code=status.HTTP_200_OK,
    tags=["orders"]
)
async def get_order_by_id(
    order_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrderSchema:
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

    return OrderSchema.model_validate(order)
