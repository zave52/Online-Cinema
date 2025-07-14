from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict

from .exapmles.shopping_cart import (
    shopping_cart_add_movie_request_schema_example,
    shopping_cart_add_movie_response_schema_example,
    shopping_cart_movie_item_schema_example,
    shopping_cart_get_movies_schema_example,
    message_response_schema_example
)


class ShoppingCartAddMovieRequestSchema(BaseModel):
    movie_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": shopping_cart_add_movie_request_schema_example
        }
    )


class ShoppingCartAddMovieResponseSchema(BaseModel):
    cart_item_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": shopping_cart_add_movie_response_schema_example
        }
    )


class MessageResponseSchema(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": message_response_schema_example
        }
    )


class ShoppingCartMovieItemSchema(BaseModel):
    cart_item_id: int
    name: str
    year: int
    price: Decimal
    genres: List[str]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": shopping_cart_movie_item_schema_example
        }
    )


class ShoppingCartGetMoviesSchema(BaseModel):
    total_items: int
    movies: List[ShoppingCartMovieItemSchema]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": shopping_cart_get_movies_schema_example
        }
    )
