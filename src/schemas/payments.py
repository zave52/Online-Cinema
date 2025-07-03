from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from database.models.payments import PaymentStatusEnum


class PaymentItemSchema(BaseModel):
    id: int
    order_item_id: int
    price_at_payment: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentSchema(BaseModel):
    id: int
    user_id: int
    order_id: int
    status: PaymentStatusEnum
    amount: Decimal
    created_at: datetime
    items: List[PaymentItemSchema]
    external_payment_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class PaymentListSchema(BaseModel):
    payments: List[PaymentSchema]
    total_pages: int
    total_items: int
    prev_page: Optional[str] = None
    next_page: Optional[str] = None


class CreatePaymentIntentSchema(BaseModel):
    order_id: int


class PaymentIntentResponseSchema(BaseModel):
    id: str
    client_secret: str
    amount: Decimal
    currency: str


class ProcessPaymentSchema(BaseModel):
    payment_intent_id: str


class RefundPaymentSchema(BaseModel):
    amount: Optional[Decimal] = None
    reason: Optional[str] = None


class CheckoutSessionRequestSchema(BaseModel):
    order_id: int
    success_url: str
    cancel_url: str


class CheckoutSessionResponseSchema(BaseModel):
    id: str
    url: str
    amount_total: Optional[Decimal]


class MessageResponseSchema(BaseModel):
    message: str
