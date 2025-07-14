from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from database.models.orders import OrderStatusEnum
from schemas.orders import (
    OrderItemSchema,
    OrderSchema,
    CreateOrderSchema,
    RefundRequestSchema,
    MessageResponseSchema,
)


class MockMovie:
    def __init__(self, name="Test Movie"):
        self.name = name


class MockOrderItemModel(Mock):
    def __init__(
        self,
        id=1,
        movie_id=101,
        price=Decimal("9.99"),
        movie_name="Test Movie",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.id = id
        self.movie_id = movie_id
        self.price_at_order = price
        self.movie = MockMovie(name=movie_name)
        self.movie_name = movie_name


@pytest.mark.validation
class TestOrderItemSchema:
    def test_valid_order_item_from_model(self):
        """Test creating OrderItemSchema from a mock model."""
        mock_model = MockOrderItemModel()
        order_item = OrderItemSchema.model_validate(mock_model)
        assert order_item.id == 1
        assert order_item.movie_id == 101
        assert order_item.movie_name == "Test Movie"
        assert order_item.price_at_order == Decimal("9.99")

    def test_order_item_direct_creation(self):
        """Test creating OrderItemSchema directly from data."""
        data = {
            "id": 2,
            "movie_id": 102,
            "movie_name": "Another Movie",
            "price_at_order": Decimal("12.50"),
        }
        order_item = OrderItemSchema(**data)
        assert order_item.id == 2
        assert order_item.movie_name == "Another Movie"


@pytest.mark.validation
class TestOrderSchema:
    def test_valid_order(self):
        """Test a valid order schema."""
        item_data = {
            "id": 1,
            "movie_id": 101,
            "movie_name": "Test Movie",
            "price_at_order": Decimal("9.99"),
        }
        order_data = {
            "id": 1,
            "user_id": 1,
            "status": OrderStatusEnum.PENDING,
            "created_at": datetime.now(),
            "total_amount": Decimal("9.99"),
            "items": [item_data],
        }
        order = OrderSchema(**order_data)
        assert order.id == 1
        assert order.status == OrderStatusEnum.PENDING
        assert len(order.items) == 1
        assert order.items[0].movie_name == "Test Movie"

    def test_invalid_status(self):
        """Test order with invalid status."""
        order_data = {
            "id": 1,
            "user_id": 1,
            "status": "invalid_status",
            "created_at": datetime.now(),
            "total_amount": Decimal("9.99"),
            "items": [],
        }
        with pytest.raises(ValidationError):
            OrderSchema(**order_data)


@pytest.mark.validation
class TestCreateOrderSchema:
    def test_valid_create_order(self):
        """Test valid create order schema."""
        data = {"cart_item_ids": [1, 2, 3]}
        schema = CreateOrderSchema(**data)
        assert schema.cart_item_ids == [1, 2, 3]

    def test_empty_cart_items(self):
        """Test create order with empty list of items."""
        data = {"cart_item_ids": []}
        schema = CreateOrderSchema(**data)
        assert schema.cart_item_ids == []

    def test_invalid_cart_item_type(self):
        """Test create order with invalid item types."""
        with pytest.raises(ValidationError):
            CreateOrderSchema(cart_item_ids=["a", "b"])


@pytest.mark.validation
class TestRefundRequestSchema:
    def test_valid_refund_request(self):
        """Test a valid refund request."""
        data = {"reason": "Accidental purchase", "amount": Decimal("10.00")}
        schema = RefundRequestSchema(**data)
        assert schema.reason == "Accidental purchase"
        assert schema.amount == Decimal("10.00")

    def test_refund_request_without_amount(self):
        """Test refund request without an amount."""
        data = {"reason": "Item not as described"}
        schema = RefundRequestSchema(**data)
        assert schema.reason == "Item not as described"
        assert schema.amount is None


@pytest.mark.validation
class TestMessageResponseSchema:
    def test_valid_message(self):
        """Test a valid message response."""
        data = {"message": "Success"}
        schema = MessageResponseSchema(**data)
        assert schema.message == "Success"
