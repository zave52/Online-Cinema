from typing import Dict, Any

shopping_cart_add_movie_schema_example: Dict[str, Any] = {
    "movie_id": 1
}

shopping_cart_movie_item_schema_example: Dict[str, Any] = {
    "cart_item_id": 1,
    "name": "The Matrix",
    "year": 1999,
    "price": "9.99",
    "genres": ["Action", "Sci-Fi"]
}

shopping_cart_get_movies_schema_example: Dict[str, Any] = {
    "total_items": 3,
    "movies": [
        {
            "cart_item_id": 1,
            "name": "The Matrix",
            "year": 1999,
            "price": "9.99",
            "genres": ["Action", "Sci-Fi"]
        },
        {
            "cart_item_id": 2,
            "name": "Inception",
            "year": 2010,
            "price": "9.99",
            "genres": ["Action", "Thriller", "Sci-Fi"]
        },
        {
            "cart_item_id": 3,
            "name": "Interstellar",
            "year": 2014,
            "price": "9.99",
            "genres": ["Adventure", "Drama", "Sci-Fi"]
        }
    ]
}

message_response_schema_example: Dict[str, Any] = {
    "message": "Movie added to cart successfully"
}
