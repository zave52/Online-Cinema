from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from database.models.payments import PaymentStatusEnum
from schemas.payments import (
    PaymentItemSchema,
    PaymentSchema,
    PaymentListSchema,
    CreatePaymentIntentSchema,
    PaymentIntentResponseSchema,
    ProcessPaymentRequestSchema,
    RefundPaymentSchema,
    CheckoutSessionRequestSchema,
    CheckoutSessionResponseSchema,
    MessageResponseSchema,
)


@pytest.mark.validation
class TestPaymentItemSchema:
    def test_valid_payment_item(self):
        data = {
            "id": 1,
            "order_item_id": 101,
            "price_at_payment": Decimal("19.99")
        }
        item = PaymentItemSchema(**data)
        assert item.id == 1
        assert item.price_at_payment == Decimal("19.99")


@pytest.mark.validation
class TestPaymentSchema:
    def test_valid_payment(self):
        item_data = {
            "id": 1,
            "order_item_id": 101,
            "price_at_payment": Decimal("19.99")
        }
        data = {
            "id": 1,
            "user_id": 1,
            "order_id": 1,
            "status": PaymentStatusEnum.SUCCESSFUL,
            "amount": Decimal("19.99"),
            "created_at": datetime.now(),
            "items": [item_data],
            "external_payment_id": "pi_12345",
        }
        payment = PaymentSchema(**data)
        assert payment.status == PaymentStatusEnum.SUCCESSFUL
        assert len(payment.items) == 1

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            PaymentSchema(
                id=1,
                user_id=1,
                order_id=1,
                status="invalid_status",
                amount=Decimal("19.99"),
                created_at=datetime.now(),
                items=[],
            )


@pytest.mark.validation
class TestPaymentListSchema:
    def test_valid_payment_list(self):
        payment_data = {
            "id": 1,
            "user_id": 1,
            "order_id": 1,
            "status": PaymentStatusEnum.SUCCESSFUL,
            "amount": Decimal("19.99"),
            "created_at": datetime.now(),
            "items": [],
            "external_payment_id": "pi_12345",
        }
        data = {
            "payments": [payment_data],
            "total_pages": 1,
            "total_items": 1,
        }
        payment_list = PaymentListSchema(**data)
        assert payment_list.total_pages == 1
        assert len(payment_list.payments) == 1


@pytest.mark.validation
class TestCreatePaymentIntentSchema:
    def test_valid_create_payment_intent(self):
        data = {"order_id": 1}
        intent = CreatePaymentIntentSchema(**data)
        assert intent.order_id == 1

    def test_invalid_order_id(self):
        with pytest.raises(ValidationError):
            CreatePaymentIntentSchema(order_id="abc")


@pytest.mark.validation
class TestPaymentIntentResponseSchema:
    def test_valid_payment_intent_response(self):
        data = {
            "id": "pi_123",
            "client_secret": "secret",
            "amount": Decimal("10.99"),
            "currency": "usd",
        }
        response = PaymentIntentResponseSchema(**data)
        assert response.id == "pi_123"


@pytest.mark.validation
class TestProcessPaymentSchema:
    def test_valid_process_payment(self):
        data = {"payment_intent_id": "pi_123"}
        schema = ProcessPaymentRequestSchema(**data)
        assert schema.payment_intent_id == "pi_123"


@pytest.mark.validation
class TestRefundPaymentSchema:
    def test_valid_refund(self):
        data = {"amount": Decimal("10.00"), "reason": "accidental"}
        schema = RefundPaymentSchema(**data)
        assert schema.amount == Decimal("10.00")
        assert schema.reason == "accidental"

    def test_partial_refund_data(self):
        data = {"reason": "not satisfied"}
        schema = RefundPaymentSchema(**data)
        assert schema.amount is None
        assert schema.reason == "not satisfied"


@pytest.mark.validation
class TestCheckoutSessionRequestSchema:
    def test_valid_checkout_request(self):
        data = {
            "order_id": 1,
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        }
        schema = CheckoutSessionRequestSchema(**data)
        assert schema.order_id == 1
        assert schema.success_url == "https://example.com/success"


@pytest.mark.validation
class TestCheckoutSessionResponseSchema:
    def test_valid_checkout_response(self):
        data = {
            "id": "cs_123",
            "url": "https://checkout.stripe.com/pay/cs_123",
            "amount_total": Decimal("99.99"),
        }
        schema = CheckoutSessionResponseSchema(**data)
        assert schema.id == "cs_123"
        assert schema.amount_total == Decimal("99.99")


@pytest.mark.validation
class TestMessageResponseSchema:
    def test_valid_message(self):
        data = {"message": "Operation successful"}
        schema = MessageResponseSchema(**data)
        assert schema.message == "Operation successful"
