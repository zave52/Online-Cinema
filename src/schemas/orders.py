from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel

from database.models.orders import OrderStatusEnum


class OrderItemSchema(BaseModel):
    id: int
    movie_id: int
    movie_name: str
    price_at_order: Decimal

    class Config:
        from_attributes = True


class OrderSchema(BaseModel):
    id: int
    user_id: int
    status: OrderStatusEnum
    created_at: datetime
    total_amount: Optional[Decimal]
    items: List[OrderItemSchema]

    class Config:
        from_attributes = True


class OrderListSchema(BaseModel):
    orders: List[OrderSchema]
    total_pages: int
    total_items: int
    prev_page: Optional[str]
    next_page: Optional[str]


class CreateOrderSchema(BaseModel):
    cart_item_ids: List[int]


class CancelOrderSchema(BaseModel):
    reason: Optional[str] = None


class RefundRequestSchema(BaseModel):
    reason: str
    amount: Optional[float] = None


class MessageResponseSchema(BaseModel):
    message: str
