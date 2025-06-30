from fastapi import (
    APIRouter,
    status,
    Depends,
    HTTPException
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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

