from datetime import datetime
from typing import List, Optional, Any
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, model_validator

from database.models.orders import OrderStatusEnum, OrderItemModel

from .exapmles.orders import (
    order_item_schema_example,
    order_schema_example,
    order_list_schema_example,
    create_order_schema_example,
    refund_request_schema_example,
    message_response_schema_example
)


class OrderItemSchema(BaseModel):
    id: int
    movie_id: int
    movie_name: str
    price_at_order: Decimal

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": order_item_schema_example
        }
    )

    @model_validator(mode="before")
    def extract_movie_name(cls, data: Any) -> Any:
        if isinstance(data, OrderItemModel):
            data.movie_name = data.movie.name
        return data


class OrderSchema(BaseModel):
    id: int
    user_id: int
    status: OrderStatusEnum
    created_at: datetime
    total_amount: Optional[Decimal]
    items: List[OrderItemSchema]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": order_schema_example
        }
    )


class OrderListSchema(BaseModel):
    orders: List[OrderSchema]
    total_pages: int
    total_items: int
    prev_page: Optional[str] = None
    next_page: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": order_list_schema_example
        }
    )


class CreateOrderSchema(BaseModel):
    cart_item_ids: List[int]

    model_config = ConfigDict(
        json_schema_extra={
            "example": create_order_schema_example
        }
    )


class RefundRequestSchema(BaseModel):
    reason: str
    amount: Optional[Decimal] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": refund_request_schema_example
        }
    )


class MessageResponseSchema(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": message_response_schema_example
        }
    )
