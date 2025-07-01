from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import (
    get_current_user,
    get_or_create_cart,
    RoleChecker
)
from database import get_db
from database.models.accounts import UserModel, UserGroupEnum
from database.models.movies import MovieModel
from database.models.shopping_cart import CartModel, CartItemModel
from database.models.orders import OrderModel, OrderItemModel, OrderStatusEnum
from schemas.shopping_cart import (
    MessageResponseSchema,
    ShoppingCartAddMovieSchema,
    ShoppingCartGetMoviesSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.post(
    "/cart/items/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["cart"]
)
async def add_movie_to_cart(
    data: ShoppingCartAddMovieSchema,
    cart: CartModel = Depends(get_or_create_cart),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    combined_stmt = select(
        MovieModel,
        CartItemModel
    ).outerjoin(
        CartItemModel,
        (CartItemModel.movie_id == MovieModel.id) &
        (CartItemModel.cart_id == cart.id)
    ).where(MovieModel.id == data.movie_id)

    result = await db.execute(combined_stmt)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    movie, cart_item = row

    if cart_item:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is already in the cart."
        )

    purchase_stmt = select(MovieModel).join(
        UserModel.purchased
    ).where(
        MovieModel.id == data.movie_id,
        UserModel.id == user.id
    )
    result = await db.execute(purchase_stmt)
    purchased = result.scalars().first()

    if purchased:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie has already been purchased."
        )

    new_cart_item = CartItemModel(cart_id=cart.id, movie_id=data.movie_id)
    db.add(new_cart_item)
    await db.commit()

    return MessageResponseSchema(
        message=f"Movie successfully added to cart with id {new_cart_item.id}."
    )


@router.delete(
    "/cart/items/{cart_item_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["cart"]
)
async def delete_movie_from_cart(
    cart_item_id: int,
    cart: CartModel = Depends(get_or_create_cart),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    cart_item_stmt = (
        select(CartItemModel)
        .where(
            CartItemModel.id == cart_item_id,
            CartItemModel.cart_id == cart.id
        )
    )
    result = await db.execute(cart_item_stmt)
    cart_item = result.scalars().first()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item with the given id was not found in your cart."
        )

    await db.delete(cart_item)
    await db.commit()

    return


@router.get(
    "/cart/",
    response_model=ShoppingCartGetMoviesSchema,
    status_code=status.HTTP_200_OK,
    tags=["cart"]
)
async def get_shopping_cart_movies(
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> ShoppingCartGetMoviesSchema:
    stmt = (
        select(CartItemModel, MovieModel)
        .join(
            MovieModel,
            CartItemModel.movie_id == MovieModel.id
        )
        .where(
            CartItemModel.cart_id == cart.id
        )
    )
    result = await db.execute(stmt)
    items_with_movies = result.all()

    movie_items = []
    for cart_item, movie in items_with_movies:
        movie_dict = {
            "cart_item_id": cart_item.id,
            "name": movie.name,
            "year": movie.year,
            "price": movie.price,
            "genres": movie.genres
        }
        movie_items.append(movie_dict)

    return ShoppingCartGetMoviesSchema(
        total_items=len(movie_items),
        movies=movie_items
    )


@router.get(
    "/cart/{cart_id}/",
    response_model=ShoppingCartGetMoviesSchema,
    status_code=status.HTTP_200_OK,
    tags=["cart", "moderator", "admin"]
)
async def get_shopping_cart_movies_by_id(
    cart_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> ShoppingCartGetMoviesSchema:
    cart_stmt = select(CartModel).where(CartModel.id == cart_id)
    result = await db.execute(cart_stmt)
    cart = result.scalars().first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping cart with the given id was not found."
        )

    items_stmt = (
        select(CartItemModel, MovieModel)
        .join(
            MovieModel,
            CartItemModel.movie_id == MovieModel.id
        )
        .where(
            CartItemModel.cart_id == cart.id
        )
    )
    result = await db.execute(items_stmt)
    items_with_movies = result.all()

    movie_items = []
    for cart_item, movie in items_with_movies:
        movie_dict = {
            "cart_item_id": cart_item.id,
            "name": movie.name,
            "year": movie.year,
            "price": movie.price,
            "genres": movie.genres
        }
        movie_items.append(movie_dict)

    return ShoppingCartGetMoviesSchema(
        total_items=len(movie_items),
        movies=movie_items
    )


@router.delete(
    "/cart/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["cart"]
)
async def clear_shopping_cart(
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id)
    result = await db.execute(stmt)
    if not result.scalars().first():
        return

    stmt = delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
    await db.execute(stmt)
    await db.commit()

    return


@router.post(
    "/cart/checkout/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["cart", "payment"]
)
async def checkout_cart_items(
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    stmt = (
        select(CartItemModel, MovieModel)
        .join(MovieModel, CartItemModel.movie_id == MovieModel.id)
        .where(CartItemModel.cart_id == cart.id)
    )
    result = await db.execute(stmt)
    items_with_movies = result.all()

    if not items_with_movies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty. Cannot proceed with checkout."
        )

    purchased_movies = []
    available_items = []

    for cart_item, movie in items_with_movies:
        purchase_check_stmt = (
            select(MovieModel)
            .join(UserModel.purchased)
            .where(
                MovieModel.id == movie.id,
                UserModel.id == user.id
            )
        )
        result = await db.execute(purchase_check_stmt)
        if result.scalars().first():
            purchased_movies.append(movie.name)
        else:
            available_items.append((cart_item, movie))

    if purchased_movies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Movies already purchased: {', '.join(purchased_movies)}"
        )

    total_amount = sum(movie.price for _, movie in available_items)

    order = OrderModel(
        user_id=user.id,
        status=OrderStatusEnum.PENDING,
        total_amount=total_amount
    )
    db.add(order)
    await db.flush()

    for cart_item, movie in available_items:
        order_item = OrderItemModel(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db.add(order_item)

    for cart_item, _ in available_items:
        await db.delete(cart_item)

    await db.commit()

    return MessageResponseSchema(
        message=f"Checkout completed successfully. Order ID: {order.id}. "
                f"Total amount: ${total_amount}. "
                f"Please proceed to payment."
    )
