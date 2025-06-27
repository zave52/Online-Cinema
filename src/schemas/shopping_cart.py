from pydantic import BaseModel


class ShoppingCartAddMovieSchema(BaseModel):
    movie_id: int


class MessageResponseSchema(BaseModel):
    message: str
