from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Integer,
    Enum as SQLEnum,
    DECIMAL,
    DateTime,
    ForeignKey,
    String
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.accounts import UserModel
from database.models.orders import OrderModel, OrderItemModel


class PaymentStatusEnum(Enum):
    """Enumeration for payment status values.

    Defines the possible states a payment can be in:
    - SUCCESSFUL: Payment was completed successfully
    - CANCELED: Payment was canceled
    - REFUNDED: Payment was refunded
    """
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentModel(Base):
    """Model representing payment transactions.

    This model stores payment information including status, amount,
    creation time, external payment ID, and relationships to users,
    orders, and payment items.
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    status: Mapped[PaymentStatusEnum] = mapped_column(
        SQLEnum(PaymentStatusEnum),
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc)
    )
    external_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="payments"
    )
    order: Mapped["OrderModel"] = relationship(
        "OrderModel",
        back_populates="payments"
    )
    items: Mapped[List["PaymentItemModel"]] = relationship(
        "PaymentItemModel",
        back_populates="payment"
    )

    def __repr__(self) -> str:
        return (f"<PaymentModel(id={self.id}, status={self.status}, "
                f"amount={self.amount}, user_id={self.user_id},"
                f"order_id={self.order_id})>")


class PaymentItemModel(Base):
    """Model representing individual items within a payment.

    This model stores information about each order item in a payment,
    including the price at the time of payment and relationships to
    the payment and order item.
    """
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    price_at_payment: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False
    )
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False
    )
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False
    )

    payment: Mapped[PaymentModel] = relationship(
        PaymentModel,
        back_populates="items"
    )
    order_item: Mapped["OrderItemModel"] = relationship(
        "OrderItemModel",
        back_populates="payment_items"
    )

    def __repr__(self) -> str:
        return (f"<PaymentItemModel(id={self.id}, "
                f"price_at_payment={self.price_at_payment}, "
                f"payment_id={self.payment_id}, "
                f"order_item_id={self.order_item_id})>")
