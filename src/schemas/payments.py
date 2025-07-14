from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from database.models.payments import PaymentStatusEnum

from .exapmles.payments import (
    payment_item_schema_example,
    payment_schema_example,
    payment_list_schema_example,
    create_payment_intent_schema_example,
    payment_intent_response_schema_example,
    process_payment_request_schema_example,
    process_payment_response_schema_example,
    refund_payment_schema_example
)


class PaymentItemSchema(BaseModel):
    id: int
    order_item_id: int
    price_at_payment: Decimal

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": payment_item_schema_example
        }
    )


class PaymentSchema(BaseModel):
    id: int
    user_id: int
    order_id: int
    status: PaymentStatusEnum
    amount: Decimal
    created_at: datetime
    items: List[PaymentItemSchema]
    external_payment_id: Optional[str]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": payment_schema_example
        }
    )


class PaymentListSchema(BaseModel):
    payments: List[PaymentSchema]
    total_pages: int
    total_items: int
    prev_page: Optional[str] = None
    next_page: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": payment_list_schema_example
        }
    )


class CreatePaymentIntentSchema(BaseModel):
    order_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": create_payment_intent_schema_example
        }
    )


class PaymentIntentResponseSchema(BaseModel):
    id: str
    client_secret: str
    amount: Decimal
    currency: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": payment_intent_response_schema_example
        }
    )


class ProcessPaymentRequestSchema(BaseModel):
    payment_intent_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": process_payment_request_schema_example
        }
    )


class ProcessPaymentResponseSchema(BaseModel):
    payment_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": process_payment_response_schema_example
        }
    )


class RefundPaymentSchema(BaseModel):
    amount: Optional[Decimal] = None
    reason: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": refund_payment_schema_example
        }
    )


class CheckoutSessionRequestSchema(BaseModel):
    order_id: int
    success_url: str
    cancel_url: str


class CheckoutSessionResponseSchema(BaseModel):
    id: str
    url: str
    amount_total: Optional[Decimal]
