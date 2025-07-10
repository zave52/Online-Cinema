from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.shopping_cart import (
    ShoppingCartAddMovieRequestSchema,
    ShoppingCartAddMovieResponseSchema,
    MessageResponseSchema,
    ShoppingCartMovieItemSchema,
    ShoppingCartGetMoviesSchema,
)


@pytest.mark.validation
class TestShoppingCartAddMovieRequestSchema:
    def test_valid_add_movie_request(self):
        """Test valid add movie request."""
        data = {"movie_id": 123}
        schema = ShoppingCartAddMovieRequestSchema(**data)
        assert schema.movie_id == 123

    def test_invalid_movie_id_type(self):
        """Test invalid movie_id type."""
        with pytest.raises(ValidationError):
            ShoppingCartAddMovieRequestSchema(movie_id="abc")


@pytest.mark.validation
class TestShoppingCartAddMovieResponseSchema:
    def test_valid_add_movie_response(self):
        """Test valid add movie response."""
        data = {"cart_item_id": 456}
        schema = ShoppingCartAddMovieResponseSchema(**data)
        assert schema.cart_item_id == 456

    def test_invalid_cart_item_id_type(self):
        """Test invalid cart_item_id type."""
        with pytest.raises(ValidationError):
            ShoppingCartAddMovieResponseSchema(cart_item_id="xyz")


@pytest.mark.validation
class TestMessageResponseSchema:
    def test_valid_message_response(self):
        """Test valid message response."""
        data = {"message": "Success"}
        schema = MessageResponseSchema(**data)
        assert schema.message == "Success"

    def test_invalid_message_type(self):
        """Test invalid message type."""
        with pytest.raises(ValidationError):
            MessageResponseSchema(message=123)


@pytest.mark.validation
class TestShoppingCartMovieItemSchema:
    def test_valid_movie_item(self):
        """Test valid shopping cart movie item."""
        data = {
            "cart_item_id": 1,
            "name": "Inception",
            "year": 2010,
            "price": Decimal("14.99"),
            "genres": ["Sci-Fi", "Action"],
        }
        schema = ShoppingCartMovieItemSchema(**data)
        assert schema.name == "Inception"
        assert len(schema.genres) == 2

    def test_invalid_field_types(self):
        """Test invalid field types for movie item."""
        with pytest.raises(ValidationError):
            ShoppingCartMovieItemSchema(
                cart_item_id="a",
                name="Inception",
                year=2010,
                price=Decimal("14.99"),
                genres=["Sci-Fi"],
            )
        with pytest.raises(ValidationError):
            ShoppingCartMovieItemSchema(
                cart_item_id=1,
                name="Inception",
                year="not-a-year",
                price=Decimal("14.99"),
                genres=["Sci-Fi"],
            )


@pytest.mark.validation
class TestShoppingCartGetMoviesSchema:
    def test_valid_get_movies_schema(self):
        """Test valid get movies schema."""
        movie_item_data = {
            "cart_item_id": 1,
            "name": "Inception",
            "year": 2010,
            "price": Decimal("14.99"),
            "genres": ["Sci-Fi", "Action"],
        }
        data = {"total_items": 1, "movies": [movie_item_data]}
        schema = ShoppingCartGetMoviesSchema(**data)
        assert schema.total_items == 1
        assert len(schema.movies) == 1
        assert schema.movies[0].name == "Inception"

    def test_empty_movies_list(self):
        """Test get movies schema with an empty list of movies."""
        data = {"total_items": 0, "movies": []}
        schema = ShoppingCartGetMoviesSchema(**data)
        assert schema.total_items == 0
        assert len(schema.movies) == 0

    def test_invalid_movies_list_type(self):
        """Test get movies schema with invalid movies list type."""
        with pytest.raises(ValidationError):
            ShoppingCartGetMoviesSchema(total_items=1, movies="not-a-list")
