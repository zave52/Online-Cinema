from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select
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
