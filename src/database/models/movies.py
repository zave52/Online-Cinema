from typing import Optional, List

from sqlalchemy import (
    Integer,
    String,
    Float,
    Text,
    DECIMAL,
    ForeignKey,
    UniqueConstraint,
    Table,
    Column
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

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
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

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
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

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
    uuid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
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

    __table_args__ = (UniqueConstraint("name", "year", "time"),)

    def __repr__(self) -> str:
        return f"<MovieModel(id={self.id}, name={self.name}, year={self.year}, time={self.time})>"
