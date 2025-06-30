from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from database.models.payments import PaymentStatusEnum


class PaymentItemSchema(BaseModel):
    id: int
    order_item_id: int
    price_at_payment: float

    class Config:
        from_attributes = True


class PaymentSchema(BaseModel):
    id: int
    user_id: int
    order_id: int
    status: PaymentStatusEnum
    amount: float
    created_at: datetime
    items: List[PaymentItemSchema]
    external_payment_id: Optional[int]

    class Config:
        from_attributes = True


class PaymentListSchema(BaseModel):
    payments: List[PaymentSchema]
    total_pages: int
    total_items: int
    prev_page: Optional[str]
    next_page: Optional[str]


class CreatePaymentIntentSchema(BaseModel):
    order_id: int


class PaymentIntentResponseSchema(BaseModel):
    id: str
    client_secret: str
    amount: float
    currency: str


class ProcessPaymentSchema(BaseModel):
    payment_intent_id: str


class RefundPaymentSchema(BaseModel):
    amount: Optional[float] = None
    reason: Optional[str] = None


class CheckoutSessionRequestSchema(BaseModel):
    order_id: int
    success_url: str
    cancel_url: str


class CheckoutSessionResponseSchema(BaseModel):
    id: str
    url: str
    amount_total: Optional[float]


class MessageResponseSchema(BaseModel):
    message: str
