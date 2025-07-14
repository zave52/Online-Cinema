from typing import Dict, Any

movie_item_schema_example: Dict[str, Any] = {
    "id": 1,
    "name": "The Matrix",
    "year": 1999,
    "time": 136,
    "imdb": 8.7,
    "votes": 1895412,
    "meta_score": 73.0,
    "gross": 171479930.0,
    "description": "A computer hacker learns from mysterious rebels about the "
                   "true nature of his reality and his role in the war against "
                   "its controllers.",
    "price": "9.99",
    "genres": [
        {"id": 1, "name": "Action"},
        {"id": 2, "name": "Sci-Fi"}
    ]
}

movie_list_response_schema_example: Dict[str, Any] = {
    "movies": [
        movie_item_schema_example,
        {
            "id": 2,
            "name": "Inception",
            "time": 148,
            "imdb": 8.8,
            "genres": [
                {"id": 1, "name": "Action"},
                {"id": 3, "name": "Thriller"}
            ],
            "description": "A thief who steals corporate secrets through the "
                           "use of dream-sharing technology is given the "
                           "inverse task of planting an idea into "
                           "the mind of a C.E.O."
        }
    ],
    "prev_page": "/api/v1/cinema/movies/?page=1&per_page=10",
    "next_page": "/api/v1/cinema/movies/?page=3&per_page=10",
    "total_pages": 5,
    "total_items": 50
}

movie_create_schema_example: Dict[str, Any] = {
    "name": "New Blockbuster Movie",
    "year": 2024,
    "time": 120,
    "imdb": 8.5,
    "votes": 1000,
    "meta_score": 85.0,
    "gross": 50000000.0,
    "description": "An exciting new movie that will captivate audiences worldwide.",
    "price": "12.99",
    "certification": "PG-13",
    "genres": ["Action", "Adventure", "Sci-Fi"],
    "stars": ["Tom Cruise", "Emily Blunt"],
    "directors": ["Christopher Nolan"]
}

movie_create_response_schema_example: Dict[str, Any] = {
    "id": 3,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "New Blockbuster Movie",
    "year": 2024,
    "time": 120,
    "imdb": 8.5,
    "votes": 1000,
    "meta_score": 85.0,
    "gross": 50000000.0,
    "description": "An exciting new movie that will captivate audiences worldwide.",
    "price": "12.99",
    "certification": {
        "id": 1,
        "name": "PG-13"
    },
    "genres": [
        {"id": 1, "name": "Action"},
        {"id": 4, "name": "Adventure"},
        {"id": 2, "name": "Sci-Fi"}
    ],
    "stars": [
        {"id": 1, "name": "Tom Cruise"},
        {"id": 2, "name": "Emily Blunt"}
    ],
    "directors": [
        {"id": 1, "name": "Christopher Nolan"}
    ]
}

movie_detail_schema_example: Dict[str, Any] = {
    **movie_create_response_schema_example,
    "likes": 1250,
    "favorites": 890,
    "average_rating": 8.7,
    "comments": [
        {
            "id": 1,
            "content": "Amazing movie! The special effects are incredible.",
            "created_at": "2024-01-15T10:30:00Z",
            "parent_id": None
        },
        {
            "id": 2,
            "content": "I agree, the plot was really well thought out.",
            "created_at": "2024-01-15T11:00:00Z",
            "parent_id": 1
        }
    ]
}

movie_update_schema_example: Dict[str, Any] = {
    "name": "Updated Movie Title",
    "year": 2024,
    "time": 125,
    "imdb": 8.6,
    "votes": 1500,
    "meta_score": 87.0,
    "gross": 55000000.0,
    "description": "Updated description for the movie.",
    "price": "13.99",
    "certification": "R",
    "genres": ["Action", "Drama"],
    "stars": ["Tom Cruise", "Emily Blunt", "John Doe"],
    "directors": ["Christopher Nolan", "Jane Smith"]
}

genre_schema_example: Dict[str, Any] = {
    "id": 1,
    "name": "Action"
}

genre_with_movie_count_schema_example: Dict[str, Any] = {
    **genre_schema_example,
    "movie_count": 150
}

genre_list_schema_example: Dict[str, Any] = {
    "genres": [
        {"id": 1, "name": "Action"},
        {"id": 2, "name": "Sci-Fi"},
        {"id": 3, "name": "Thriller"},
        {"id": 4, "name": "Adventure"},
        {"id": 5, "name": "Drama"}
    ],
    "prev_page": None,
    "next_page": "/api/v1/cinema/genres/?page=2&per_page=5",
    "total_pages": 3,
    "total_items": 15
}

star_schema_example: Dict[str, Any] = {
    "id": 1,
    "name": "Keanu Reeves"
}

star_list_schema_example: Dict[str, Any] = {
    "stars": [
        {"id": 1, "name": "Keanu Reeves"},
        {"id": 2, "name": "Tom Cruise"},
        {"id": 3, "name": "Emily Blunt"},
        {"id": 4, "name": "Leonardo DiCaprio"},
        {"id": 5, "name": "Brad Pitt"}
    ],
    "prev_page": None,
    "next_page": "/api/v1/cinema/stars/?page=2&per_page=5",
    "total_pages": 4,
    "total_items": 20
}

director_schema_example: Dict[str, Any] = {
    "id": 1,
    "name": "Lana Wachowski"
}

director_list_schema_example: Dict[str, Any] = {
    "directors": [
        {"id": 1, "name": "Lana Wachowski"},
        {"id": 2, "name": "Christopher Nolan"},
        {"id": 3, "name": "Quentin Tarantino"},
        {"id": 4, "name": "Steven Spielberg"},
        {"id": 5, "name": "James Cameron"}
    ],
    "prev_page": None,
    "next_page": "/api/v1/cinema/directors/?page=2&per_page=5",
    "total_pages": 2,
    "total_items": 10
}

certification_schema_example: Dict[str, Any] = {
    "id": 1,
    "name": "PG-13"
}

comment_schema_example: Dict[str, Any] = {
    "id": 1,
    "content": "This movie was absolutely fantastic! "
               "The plot twists were unexpected and the acting was superb.",
    "created_at": "2024-01-15T10:30:00Z",
    "parent_id": None
}

comment_movie_request_schema_example: Dict[str, Any] = {
    "content": "Great movie! Highly recommended."
}

name_schema_example: Dict[str, Any] = {
    "name": "New Genre"
}

rate_movie_schema_example: Dict[str, Any] = {
    "rate": 9
}

message_response_schema_example: Dict[str, Any] = {
    "message": "Operation completed successfully"
}
