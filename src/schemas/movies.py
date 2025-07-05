from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .exapmles.movies import (
    movie_item_schema_example,
    movie_list_response_schema_example,
    movie_create_schema_example,
    movie_create_response_schema_example,
    movie_detail_schema_example,
    movie_update_schema_example,
    genre_schema_example,
    genre_with_movie_count_schema_example,
    genre_list_schema_example,
    star_schema_example,
    star_list_schema_example,
    director_schema_example,
    director_list_schema_example,
    certification_schema_example,
    comment_schema_example,
    comment_movie_request_schema_example,
    name_schema_example,
    rate_movie_schema_example,
    message_response_schema_example,
)


class BaseListSchema(BaseModel):
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


class GenreSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": genre_schema_example
        }
    )


class GenreWithMovieCountSchema(GenreSchema):
    movie_count: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": genre_with_movie_count_schema_example
        }
    )


class GenreListSchema(BaseListSchema):
    genres: List[GenreSchema]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": genre_list_schema_example
        }
    )


class StarSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": star_schema_example
        }
    )


class StarListSchema(BaseListSchema):
    stars: List[StarSchema]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": star_list_schema_example
        }
    )


class DirectorSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": director_schema_example
        }
    )


class DirectorListSchema(BaseListSchema):
    directors: List[DirectorSchema]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": director_list_schema_example
        }
    )


class CertificationSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": certification_schema_example
        }
    )


class CommentSchema(BaseModel):
    id: int
    content: str
    created_at: datetime
    parent_id: Optional[int]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": comment_schema_example
        }
    )


class CommentMovieRequestSchema(BaseModel):
    content: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": comment_movie_request_schema_example
        }
    )


class NameSchema(BaseModel):
    name: str = Field(..., max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": name_schema_example
        }
    )


class MovieBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0)
    meta_score: float = Field(..., ge=0, le=100)
    gross: float = Field(..., ge=0)
    description: str
    price: Decimal = Field(..., max_digits=10, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)


class MovieBaseExtendedSchema(MovieBaseSchema):
    id: int
    uuid: UUID
    certification: CertificationSchema
    genres: List[GenreSchema]
    stars: List[StarSchema]
    directors: List[DirectorSchema]


class MovieDetailSchema(MovieBaseExtendedSchema):
    likes: int
    favorites: int
    average_rating: float
    comments: List[CommentSchema]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": movie_detail_schema_example
        }
    )


class MovieListItemSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=255)
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0)
    genres: List[GenreSchema]
    description: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": movie_item_schema_example
        }
    )


class MovieListResponseSchema(BaseListSchema):
    movies: List[MovieListItemSchema]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": movie_list_response_schema_example
        }
    )


class MovieCreateRequestSchema(MovieBaseSchema):
    certification: str
    genres: List[str]
    stars: List[str]
    directors: List[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": movie_create_schema_example
        }
    )

    @field_validator("certification")
    @classmethod
    def normalize_certification(cls, value: str) -> str:
        return value.upper()

    @field_validator("genres", "stars", "directors")
    @classmethod
    def normalize_list_fields(cls, value: List[str]) -> List[str]:
        return [item.title() for item in value]


class MovieCreateResponseSchema(MovieBaseExtendedSchema):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": movie_create_response_schema_example
        }
    )


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    year: Optional[int] = None
    time: Optional[int] = Field(None, ge=0)
    imdb: Optional[float] = Field(None, ge=0, le=10)
    votes: Optional[int] = Field(None, ge=0)
    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    certification: Optional[str] = None
    genres: Optional[List[str]] = None
    stars: Optional[List[str]] = None
    directors: Optional[List[str]] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": movie_update_schema_example
        }
    )


class MessageResponseSchema(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": message_response_schema_example
        }
    )


class RateMovieSchema(BaseModel):
    rate: int = Field(..., ge=1, le=10)

    model_config = ConfigDict(
        json_schema_extra={
            "example": rate_movie_schema_example
        }
    )
