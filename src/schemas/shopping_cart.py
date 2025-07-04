from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict


class ShoppingCartAddMovieSchema(BaseModel):
    movie_id: int


class MessageResponseSchema(BaseModel):
    message: str


class ShoppingCartMovieItemSchema(BaseModel):
    cart_item_id: int
    name: str
    year: int
    price: Decimal
    genres: List[str]

    model_config = ConfigDict(from_attributes=True)


class ShoppingCartGetMoviesSchema(BaseModel):
    total_items: int
    movies: List[ShoppingCartMovieItemSchema]

    model_config = ConfigDict(from_attributes=True)
