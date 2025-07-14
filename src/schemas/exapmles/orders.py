from typing import Dict, Any

order_item_schema_example: Dict[str, Any] = {
    "id": 1,
    "movie_id": 1,
    "movie_name": "The Matrix",
    "price_at_order": "9.99"
}

order_schema_example: Dict[str, Any] = {
    "id": 1,
    "user_id": 1,
    "status": "pending",
    "created_at": "2024-01-15T10:30:00Z",
    "total_amount": "29.97",
    "items": [
        {
            "id": 1,
            "movie_id": 1,
            "movie_name": "The Matrix",
            "price_at_order": "9.99"
        },
        {
            "id": 2,
            "movie_id": 2,
            "movie_name": "Inception",
            "price_at_order": "9.99"
        },
        {
            "id": 3,
            "movie_id": 3,
            "movie_name": "Interstellar",
            "price_at_order": "9.99"
        }
    ]
}

order_list_schema_example: Dict[str, Any] = {
    "orders": [
        {
            "id": 1,
            "user_id": 1,
            "status": "pending",
            "created_at": "2024-01-15T10:30:00Z",
            "total_amount": "29.97",
            "items": [
                {
                    "id": 1,
                    "movie_id": 1,
                    "movie_name": "The Matrix",
                    "price_at_order": "9.99"
                },
                {
                    "id": 2,
                    "movie_id": 2,
                    "movie_name": "Inception",
                    "price_at_order": "9.99"
                },
                {
                    "id": 3,
                    "movie_id": 3,
                    "movie_name": "Interstellar",
                    "price_at_order": "9.99"
                }
            ]
        },
        {
            "id": 2,
            "user_id": 1,
            "status": "paid",
            "created_at": "2024-01-14T15:45:00Z",
            "total_amount": "19.98",
            "items": [
                {
                    "id": 4,
                    "movie_id": 4,
                    "movie_name": "The Dark Knight",
                    "price_at_order": "9.99"
                },
                {
                    "id": 5,
                    "movie_id": 5,
                    "movie_name": "Pulp Fiction",
                    "price_at_order": "9.99"
                }
            ]
        }
    ],
    "total_pages": 2,
    "total_items": 5,
    "prev_page": None,
    "next_page": "/api/v1/orders/?page=2&per_page=10"
}

create_order_schema_example: Dict[str, Any] = {
    "cart_item_ids": [1, 2, 3]
}

refund_request_schema_example: Dict[str, Any] = {
    "reason": "requested_by_customer",
    "amount": "29.97"
}

message_response_schema_example: Dict[str, Any] = {
    "message": "Order created successfully"
}
