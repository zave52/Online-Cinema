from typing import List

from pydantic import BaseModel


class ShoppingCartAddMoviesSchema(BaseModel):
    movie_ids: List[int]


class MessageResponseSchema(BaseModel):
    message: str
