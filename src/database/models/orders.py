from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Integer,
    ForeignKey,
    DateTime,
    Enum as SQLEnum,
    DECIMAL,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.accounts import UserModel
from database.models.movies import MovieModel


class OrderStatusEnum(Enum):
    """Enumeration for order status values.

    Defines the possible states an order can be in:
    - PENDING: Order created but not yet paid
    - PAID: Order has been successfully paid
    - CANCELED: Order has been canceled
    """
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
    """Model representing user orders.

    This model stores order information including status, creation time,
    total amount, and relationships to users, order items, and payments.
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        SQLEnum(OrderStatusEnum),
        nullable=False,
        default=OrderStatusEnum.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc)
    )
    total_amount: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2),
        nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="orders"
    )
    items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="order"
    )
    payments: Mapped[List["PaymentModel"]] = relationship(
        "PaymentModel",
        back_populates="order"
    )

    def __repr__(self) -> str:
        return (f"<OrderModel(id={self.id}, status={self.status}, "
                f"total_amount={self.total_amount})>")


class OrderItemModel(Base):
    """Model representing individual items within an order.

    This model stores information about each movie item in an order,
    including the price at the time of order and relationships to
    the order, movie, and payment items.
    """
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    price_at_order: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )

    order: Mapped[OrderModel] = relationship(
        OrderModel,
        back_populates="items"
    )
    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
        back_populates="order_items"
    )
    payment_items: Mapped[List["PaymentItemModel"]] = relationship(
        "PaymentItemModel",
        back_populates="order_item"
    )

    __table_args__ = (UniqueConstraint("order_id", "movie_id"),)

    def __repr__(self) -> str:
        return (f"<OrderItemModel(id={self.id}, "
                f"price_at_order={self.price_at_order}, "
                f"order_id={self.order_id}, movie_id={self.movie_id})>")
