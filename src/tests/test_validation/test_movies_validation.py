from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.movies import (
    GenreSchema,
    StarSchema,
    DirectorSchema,
    NameSchema,
    MovieBaseSchema,
    MovieCreateRequestSchema,
    MovieUpdateSchema,
    RateMovieSchema,
    CommentMovieRequestSchema,
)


@pytest.mark.validation
class TestNameBasedSchemas:
    """Tests for schemas with a 'name' field."""

    @pytest.mark.parametrize(
        "Schema", [GenreSchema, StarSchema, DirectorSchema, NameSchema]
    )
    def test_valid_name(self, Schema):
        """Test valid name."""
        data = {"name": "Valid Name"}
        if Schema != NameSchema:
            data["id"] = 1
        instance = Schema(**data)
        assert instance.name == "Valid Name"

    @pytest.mark.parametrize(
        "Schema", [GenreSchema, StarSchema, DirectorSchema, NameSchema]
    )
    def test_invalid_name_too_long(self, Schema):
        """Test that a name longer than 100 characters raises a ValidationError."""
        data = {"name": "a" * 101}
        if Schema != NameSchema:
            data["id"] = 1
        with pytest.raises(ValidationError):
            Schema(**data)


@pytest.mark.validation
class TestMovieBaseSchema:
    """Tests for the MovieBaseSchema."""

    def test_valid_movie_base(self):
        """Test valid movie base data."""
        data = {
            "name": "Inception",
            "year": 2010,
            "time": 148,
            "imdb": 8.8,
            "votes": 2000000,
            "meta_score": 74.0,
            "gross": 829.9,
            "description": "A mind-bending thriller.",
            "price": Decimal("12.99"),
        }
        movie = MovieBaseSchema(**data)
        assert movie.name == "Inception"

    @pytest.mark.parametrize(
        "field, value",
        [
            ("time", -1),
            ("imdb", 10.1),
            ("imdb", -0.1),
            ("votes", -1),
            ("meta_score", 100.1),
            ("meta_score", -0.1),
            ("gross", -0.1),
            ("price", Decimal("100000000.00")),
            ("price", Decimal("1.123")),
        ],
    )
    def test_invalid_movie_base_fields(self, field, value):
        """Test invalid movie base fields."""
        valid_data = {
            "name": "Inception",
            "year": 2010,
            "time": 148,
            "imdb": 8.8,
            "votes": 2000000,
            "meta_score": 74.0,
            "gross": 829.9,
            "description": "A mind-bending thriller.",
            "price": Decimal("12.99"),
        }
        invalid_data = valid_data.copy()
        invalid_data[field] = value
        with pytest.raises(ValidationError):
            MovieBaseSchema(**invalid_data)


@pytest.mark.validation
class TestMovieCreateRequestSchema:
    """Tests for the MovieCreateRequestSchema."""

    def test_field_normalization(self):
        """Test that fields are correctly normalized."""
        data = {
            "name": "Inception",
            "year": 2010,
            "time": 148,
            "imdb": 8.8,
            "votes": 2000000,
            "meta_score": 74.0,
            "gross": 829.9,
            "description": "A mind-bending thriller.",
            "price": Decimal("12.99"),
            "certification": "pg-13",
            "genres": ["action", "sci-fi"],
            "stars": ["leonardo dicaprio", "joseph gordon-levitt"],
            "directors": ["christopher nolan"],
        }
        movie = MovieCreateRequestSchema(**data)
        assert movie.certification == "PG-13"
        assert movie.genres == ["Action", "Sci-Fi"]
        assert movie.stars == ["Leonardo Dicaprio", "Joseph Gordon-Levitt"]
        assert movie.directors == ["Christopher Nolan"]


@pytest.mark.validation
class TestMovieUpdateSchema:
    """Tests for the MovieUpdateSchema."""

    def test_valid_movie_update(self):
        """Test valid partial movie update."""
        data = {"name": "Inception II", "year": 2022}
        update = MovieUpdateSchema(**data)
        assert update.name == "Inception II"
        assert update.year == 2022

    def test_invalid_movie_update(self):
        """Test invalid partial movie update."""
        with pytest.raises(ValidationError):
            MovieUpdateSchema(time=-10)


@pytest.mark.validation
class TestRateMovieSchema:
    """Tests for the RateMovieSchema."""

    @pytest.mark.parametrize("rate", [1, 5, 10])
    def test_valid_rate(self, rate):
        """Test valid movie ratings."""
        RateMovieSchema(rate=rate)

    @pytest.mark.parametrize("rate", [0, 11])
    def test_invalid_rate(self, rate):
        """Test invalid movie ratings."""
        with pytest.raises(ValidationError):
            RateMovieSchema(rate=rate)


@pytest.mark.validation
class TestCommentMovieRequestSchema:
    """Tests for the CommentMovieRequestSchema."""

    def test_valid_comment(self):
        """Test a valid comment."""
        data = {"content": "This is a great movie!"}
        comment = CommentMovieRequestSchema(**data)
        assert comment.content == "This is a great movie!"
