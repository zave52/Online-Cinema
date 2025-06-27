from datetime import datetime
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
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
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

    __table_args__ = (UniqueConstraint("name", "year", "time"),)

    def __repr__(self) -> str:
        return f"<MovieModel(id={self.id}, name={self.name}, year={self.year}, time={self.time})>"


class LikeModel(Base):
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
        return f"<LikeModel(id={self.id}, movie_id={self.movie_id}, user_id={self.user_id})>"


class CommentModel(Base):
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
        default=datetime.utcnow()
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
        return f"<CommentModel(id={self.id}, content={self.content}, movie_id={self.movie_id}, user_id={self.user_id})>"


class FavoriteMovieModel(Base):
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
        return f"<FavoriteMovieModel(id={self.id}, movie_id={self.movie_id}, user_id={self.user_id})>"


class RateMovieModel(Base):
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
        CheckConstraint("rate >= 1 AND rate <= 10", name="rate_check"),
    )

    def __repr__(self) -> str:
        return f"<RateMovieModel(id={self.id}, movie_id={self.movie_id}, user_id={self.user_id})>"
