from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from sqlalchemy import Integer, ForeignKey, DateTime, Enum as SQLEnum, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class OrderStatusEnum(Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
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
    total_amount: Optional[Mapped[float]] = mapped_column(
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
    payments: Mapped[List["OrderModel"]] = relationship(
        "OrderModel",
        back_populates="order"
    )

    def __repr__(self) -> str:
        return (f"<OrderModel(id={self.id}, status={self.status}, "
                f"total_amount={self.total_amount})>")


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    price_at_order: Mapped[float] = mapped_column(
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

    def __repr__(self) -> str:
        return (f"<OrderItemModel(id={self.id}, "
                f"price_at_order={self.price_at_order}, "
                f"order_id={self.order_id}, movie_id={self.movie_id})>")
