from typing import Dict, Any

payment_item_schema_example: Dict[str, Any] = {
    "id": 1,
    "order_item_id": 1,
    "price_at_payment": "9.99"
}

payment_schema_example: Dict[str, Any] = {
    "id": 1,
    "user_id": 1,
    "order_id": 1,
    "status": "succeeded",
    "amount": "29.97",
    "created_at": "2024-01-15T10:30:00Z",
    "items": [
        {
            "id": 1,
            "order_item_id": 1,
            "price_at_payment": "9.99"
        },
        {
            "id": 2,
            "order_item_id": 2,
            "price_at_payment": "9.99"
        },
        {
            "id": 3,
            "order_item_id": 3,
            "price_at_payment": "9.99"
        }
    ],
    "external_payment_id": "pi_1234567890abcdef"
}

payment_list_schema_example: Dict[str, Any] = {
    "payments": [
        {
            "id": 1,
            "user_id": 1,
            "order_id": 1,
            "status": "succeeded",
            "amount": "29.97",
            "created_at": "2024-01-15T10:30:00Z",
            "items": [
                {
                    "id": 1,
                    "order_item_id": 1,
                    "price_at_payment": "9.99"
                },
                {
                    "id": 2,
                    "order_item_id": 2,
                    "price_at_payment": "9.99"
                },
                {
                    "id": 3,
                    "order_item_id": 3,
                    "price_at_payment": "9.99"
                }
            ],
            "external_payment_id": "pi_1234567890abcdef"
        },
        {
            "id": 2,
            "user_id": 1,
            "order_id": 2,
            "status": "succeeded",
            "amount": "19.98",
            "created_at": "2024-01-14T15:45:00Z",
            "items": [
                {
                    "id": 4,
                    "order_item_id": 4,
                    "price_at_payment": "9.99"
                },
                {
                    "id": 5,
                    "order_item_id": 5,
                    "price_at_payment": "9.99"
                }
            ],
            "external_payment_id": "pi_0987654321fedcba"
        }
    ],
    "total_pages": 2,
    "total_items": 5,
    "prev_page": None,
    "next_page": "/api/v1/payments/?page=2&per_page=10"
}

create_payment_intent_schema_example: Dict[str, Any] = {
    "order_id": 1
}

payment_intent_response_schema_example: Dict[str, Any] = {
    "id": "pi_1234567890abcdef",
    "client_secret": "pi_1234567890abcdef_secret_abc123def456",
    "amount": "29.97",
    "currency": "usd"
}

process_payment_request_schema_example: Dict[str, Any] = {
    "payment_intent_id": "pi_1234567890abcdef"
}

process_payment_response_schema_example: Dict[str, Any] = {
    "payment_id": 1
}

refund_payment_schema_example: Dict[str, Any] = {
    "amount": "29.97",
    "reason": "Customer requested refund"
}
