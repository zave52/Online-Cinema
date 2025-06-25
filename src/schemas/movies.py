from typing import List, Any, Optional
from uuid import UUID

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


class MovieCreateRequestSchema(MovieBaseSchema):
    certification: str
    genres: List[str]
    stars: List[str]
    directors: List[str]

    @field_validator("certification")
    @classmethod
    def normalize_certification(cls, value: str) -> str:
        return value.upper()

    @field_validator("genres", "stars", "directors")
    @classmethod
    def normalize_list_fields(cls, value: List[str]) -> List[str]:
        return [item.title() for item in value]


class MovieCreateResponseSchema(MovieBaseExtendedSchema):
    pass


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    year: Optional[int] = None
    time: Optional[int] = Field(None, ge=0)
    imdb: Optional[float] = Field(None, ge=0, le=10)
    votes: Optional[int] = Field(None, ge=0)
    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None
    price: Optional[float] = Field(None, max_digits=10, decimal_places=2)
    certification: Optional[str] = None
    genres: Optional[List[str]] = None
    stars: Optional[List[str]] = None
    directors: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)
