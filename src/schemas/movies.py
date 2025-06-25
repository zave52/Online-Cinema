from typing import List, Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenreSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(from_attributes=True)


class StarSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(from_attributes=True)


class DirectorSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(from_attributes=True)


class CertificationSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(from_attributes=True)


class CommentSchema(BaseModel):
    id: int
    content: str

    model_config = ConfigDict(from_attributes=True)


class MovieBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0)
    meta_score: float = Field(..., ge=0, le=100)
    gross: float = Field(..., ge=0)
    description: str
    price: float = Field(..., max_digits=10, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)


class MovieListItemSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=255)
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0)
    genres: List[GenreSchema]
    description: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("genres", model="before")
    @classmethod
    def genres_as_list_of_names(cls, v: Any) -> List[str]:
        if not v:
            return []
        return [genre.name for genre in v]


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)
