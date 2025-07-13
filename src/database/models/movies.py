from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID as PY_UUID, uuid4

from sqlalchemy import (
    Integer,
    String,
    Float,
    Text,
    DECIMAL,
    ForeignKey,
    UniqueConstraint,
    Table,
    Column,
    UUID,
    DateTime,
    CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.accounts import UserModel
from database.models.base import Base

movie_genre_association = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "genre_id",
        Integer,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True
    )
)

movie_star_association = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "star_id",
        Integer,
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True
    )
)

movie_director_association = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "director_id",
        Integer,
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class GenreModel(Base):
    """Model representing movie genres.

    This model stores different movie genres that can be associated
    with movies through a many-to-many relationship.
    """
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary=movie_genre_association,
        back_populates="genres"
    )

    def __repr__(self) -> str:
        return f"<GenreModel(id={self.id}, name={self.name})>"


class StarModel(Base):
    """Model representing movie stars/actors.

    This model stores information about movie stars that can be associated
    with movies through a many-to-many relationship.
    """
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary=movie_star_association,
        back_populates="stars"
    )

    def __repr__(self) -> str:
        return f"<StarModel(id={self.id}, name={self.name})>"


class DirectorModel(Base):
    """Model representing movie directors.

    This model stores information about movie directors that can be associated
    with movies through a many-to-many relationship.
    """
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary=movie_director_association,
        back_populates="directors"
    )

    def __repr__(self) -> str:
        return f"<DirectorModel(id={self.id}, name={self.name})>"


class CertificationModel(Base):
    """Model representing movie certifications/ratings.

    This model stores different movie certifications (e.g., G, PG, R)
    that can be associated with movies.
    """
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        back_populates="certification"
    )

    def __repr__(self) -> str:
        return f"<CertificationModel(id={self.id}, name={self.name})>"


class MovieModel(Base):
    """Model representing movies in the cinema system.

    This is the main model for movies, containing all movie information
    including title, year, duration, ratings, price, and relationships
    to genres, stars, directors, and user interactions.
    """
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    uuid: Mapped[PY_UUID] = mapped_column(
        UUID,
        unique=True,
        nullable=False,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False
    )

    certification: Mapped[CertificationModel] = relationship(
        CertificationModel,
        back_populates="movies"
    )
    genres: Mapped[List[GenreModel]] = relationship(
        GenreModel,
        secondary=movie_genre_association,
        back_populates="movies"
    )
    directors: Mapped[List[DirectorModel]] = relationship(
        DirectorModel,
        secondary=movie_director_association,
        back_populates="movies"
    )
    stars: Mapped[List[StarModel]] = relationship(
        StarModel,
        secondary=movie_star_association,
        back_populates="movies"
    )
    likes: Mapped[List["LikeModel"]] = relationship(
        "LikeModel",
        back_populates="movie"
    )
    comments: Mapped[List["CommentModel"]] = relationship(
        "CommentModel",
        back_populates="movie"
    )
    favorites: Mapped[List["FavoriteMovieModel"]] = relationship(
        "FavoriteMovieModel",
        back_populates="movie"
    )
    rates: Mapped[List["RateMovieModel"]] = relationship(
        "RateMovieModel",
        back_populates="movie"
    )
    cart_items: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="movie"
    )
    order_items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="movie"
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time"),
        CheckConstraint("year >= 1888", name="check_year_valid"),
        CheckConstraint("time > 0", name="check_time_positive"),
        CheckConstraint("imdb >= 0 AND imdb <= 10", name="check_imdb_range"),
        CheckConstraint("votes >= 0", name="check_votes_positive"),
        CheckConstraint(
            "meta_score IS NULL OR (meta_score >= 0 AND meta_score <= 100)",
            name="check_meta_score_range"
        ),
        CheckConstraint(
            "gross IS NULL OR gross >= 0",
            name="check_gross_positive"
        ),
        CheckConstraint("price >= 0", name="check_price_positive"),
    )

    def __repr__(self) -> str:
        return f"<MovieModel(id={self.id}, name={self.name}, year={self.year}, time={self.time})>"


class LikeModel(Base):
    """Model representing user likes for movies.

    This model tracks which users have liked which movies,
    creating a many-to-many relationship between users and movies.
    """
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    movie: Mapped[MovieModel] = relationship(
        MovieModel,
        back_populates="likes",
    )
    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="likes"
    )

    __table_args__ = (UniqueConstraint("movie_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<LikeModel(id={self.id}, user_id={self.user_id}, movie_id={self.movie_id})>"


class CommentModel(Base):
    """Model representing user comments on movies.

    This model stores user comments on movies, supporting nested replies
    through a self-referencing relationship.
    """
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc)
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True
    )

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    movie: Mapped[MovieModel] = relationship(
        MovieModel,
        back_populates="comments"
    )
    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="comments"
    )
    replies: Mapped[List["CommentModel"]] = relationship(
        "CommentModel",
        backref="parent",
        remote_side=[id]
    )

    def __repr__(self) -> str:
        return f"<CommentModel(id={self.id}, user_id={self.user_id}, movie_id={self.movie_id})>"


class FavoriteMovieModel(Base):
    """Model representing user favorite movies.

    This model tracks which movies users have marked as favorites,
    creating a many-to-many relationship between users and movies.
    """
    __tablename__ = "favorite_movies"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    movie: Mapped[MovieModel] = relationship(
        MovieModel,
        back_populates="favorites"
    )
    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="favorite_movies"
    )

    __table_args__ = (UniqueConstraint("movie_id", "user_id"),)

    def __repr__(self) -> str:
        return (
            f"<FavoriteMovieModel(id={self.id}, user_id={self.user_id}, "
            f"movie_id={self.movie_id})>"
        )


class RateMovieModel(Base):
    """Model representing user ratings for movies.

    This model tracks user ratings (1-10 scale) for movies,
    creating a many-to-many relationship between users and movies.
    """
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    rate: Mapped[int] = mapped_column(Integer, nullable=False)

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    movie: Mapped[MovieModel] = relationship(
        MovieModel,
        back_populates="rates"
    )
    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="rate_movies"
    )

    __table_args__ = (
        UniqueConstraint("movie_id", "user_id"),
        CheckConstraint("rate >= 1 AND rate <= 10", name="check_rate_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<RateMovieModel(user_id={self.user_id}, movie_id={self.movie_id}, "
            f"rate={self.rate})>"
        )
