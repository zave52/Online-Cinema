from typing import List, Any

from pydantic import BaseModel, ConfigDict, field_validator


class ShoppingCartAddMovieSchema(BaseModel):
    movie_id: int


class MessageResponseSchema(BaseModel):
    message: str


class ShoppingCartMovieItemSchema(BaseModel):
    cart_item_id: int
    name: str
    year: int
    price: float
    genres: List[str]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("genres")
    @classmethod
    def genres_as_list_of_names(cls, value: Any) -> List[str]:
        if not value:
            return []
        return [genre.name for genre in value]


class ShoppingCartGetMoviesSchema(BaseModel):
    total_items: int
    movies: List[ShoppingCartMovieItemSchema]

    model_config = ConfigDict(from_attributes=True)
