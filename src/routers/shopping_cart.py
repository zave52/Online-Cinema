from decimal import Decimal

from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    ShoppingCartAddMovieRequestSchema,
    ShoppingCartAddMovieResponseSchema,
    ShoppingCartGetMoviesSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.post(
    "/cart/items/",
    response_model=ShoppingCartAddMovieResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Add movie to cart",
    description="Add a movie to the user's shopping cart. Validates that the movie is not already purchased.",
    responses={
        200: {
            "description": "Movie added to cart successfully",
            "content": {
                "application/json": {
                    "example": {
                        "catr_item_id": 1
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
            "description": "Movie not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with the given id was not found."
                    }
                }
            }
        },
        409: {
            "description": "Movie already in cart or already purchased",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie is already in the cart."
                    }
                }
            }
        },
        409: {
            "description": "Movie already purchased",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie has already been purchased."
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
                                "loc": ["body", "movie_id"],
                                "msg": "ensure this value is greater than 0",
                                "type": "value_error.number.not_gt"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def add_movie_to_cart(
    data: ShoppingCartAddMovieRequestSchema,
    cart: CartModel = Depends(get_or_create_cart),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ShoppingCartAddMovieResponseSchema:
    """Add a movie to the user's shopping cart.

    Args:
        data (ShoppingCartAddMovieSchema): Data containing the movie ID to add.
        cart (CartModel): User's shopping cart.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        MessageResponseSchema: Success message with cart item ID.
    """
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

    return ShoppingCartAddMovieResponseSchema(cart_item_id=new_cart_item.id)


@router.delete(
    "/cart/items/{cart_item_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove movie from cart",
    description="Remove a specific movie item from the user's shopping cart.",
    responses={
        204: {
            "description": "Movie removed from cart successfully"
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
            "description": "Cart item not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cart item with the given id was not found in your cart."
                    }
                }
            }
        }
    }
)
async def delete_movie_from_cart(
    cart_item_id: int,
    cart: CartModel = Depends(get_or_create_cart),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove a movie item from the user's shopping cart.

    Args:
        cart_item_id (int): The ID of the cart item to remove.
        cart (CartModel): User's shopping cart.
        user (UserModel): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        None
    """
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
    summary="Get shopping cart",
    description="Retrieve all movies in the current user's shopping cart with details.",
    responses={
        200: {
            "description": "Shopping cart contents returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "cart_id": 1,
                        "total_price": "29.97",
                        "movies": [
                            {
                                "id": 1,
                                "name": "The Shawshank Redemption",
                                "year": 1994,
                                "price": "9.99",
                                "imdb": 9.3,
                                "time": 142,
                                "genres": [{"id": 1, "name": "Drama"}]
                            },
                            {
                                "id": 2,
                                "name": "The Godfather",
                                "year": 1972,
                                "price": "9.99",
                                "imdb": 9.2,
                                "time": 175,
                                "genres": [{"id": 2, "name": "Crime"}]
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
        }
    }
)
async def get_shopping_cart_movies(
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> ShoppingCartGetMoviesSchema:
    """Retrieve all movies in the user's shopping cart.

    Args:
        user (UserModel): The current authenticated user.
        cart (CartModel): User's shopping cart.
        db (AsyncSession): Database session dependency.

    Returns:
        ShoppingCartGetMoviesSchema: Shopping cart contents with movie details.
    """
    stmt = (
        select(CartItemModel, MovieModel)
        .options(selectinload(MovieModel.genres))
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
            "genres": [genre.name for genre in movie.genres]
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
    tags=["cart", "moderator"],
    summary="Get cart by ID (Admin)",
    description="Retrieve shopping cart contents by cart ID. Only moderators and admins can access.",
    responses={
        200: {
            "description": "Shopping cart contents returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "cart_id": 1,
                        "total_price": "29.97",
                        "movies": [
                            {
                                "id": 1,
                                "name": "The Shawshank Redemption",
                                "year": 1994,
                                "price": "9.99",
                                "imdb": 9.3,
                                "time": 142,
                                "genres": [{"id": 1, "name": "Drama"}]
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
        404: {
            "description": "Cart not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Shopping cart with the given id was not found."
                    }
                }
            }
        }
    }
)
async def get_shopping_cart_movies_by_id(
    cart_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> ShoppingCartGetMoviesSchema:
    """Retrieve shopping cart contents by cart ID.

    Args:
        cart_id (int): The ID of the cart to retrieve.
        authorized: Dependency to check moderator/admin rights.
        db (AsyncSession): Database session dependency.

    Returns:
        ShoppingCartGetMoviesSchema: Shopping cart contents with movie details.
    """
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
        .options(selectinload(MovieModel.genres))
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
            "genres": [genre.name for genre in movie.genres]
        }
        movie_items.append(movie_dict)

    return ShoppingCartGetMoviesSchema(
        total_items=len(movie_items),
        movies=movie_items
    )


@router.delete(
    "/cart/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear shopping cart",
    description="Remove all items from the user's shopping cart.",
    responses={
        204: {
            "description": "Shopping cart cleared successfully"
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
        }
    }
)
async def clear_shopping_cart(
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove all items from the user's shopping cart.

    Args:
        user (UserModel): The current authenticated user.
        cart (CartModel): User's shopping cart.
        db (AsyncSession): Database session dependency.

    Returns:
        None
    """
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
    summary="Checkout cart",
    description="Create an order from all items in the shopping cart and redirect to payment.",
    responses={
        200: {
            "description": "Checkout initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Order created successfully. Redirecting to payment..."
                    }
                }
            }
        },
        400: {
            "description": "Cart is empty or checkout failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot checkout empty cart."
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
            "description": "Some movies already purchased or in pending orders",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Some movies in your cart have already been purchased."
                    }
                }
            }
        }
    }
)
async def checkout_cart_items(
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Create an order from all items in the shopping cart.

    Args:
        user (UserModel): The current authenticated user.
        cart (CartModel): User's shopping cart.
        db (AsyncSession): Database session dependency.

    Returns:
        MessageResponseSchema: Success message with order information.
    """
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
        total_amount=Decimal(total_amount)
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
