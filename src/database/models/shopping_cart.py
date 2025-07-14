from datetime import datetime, timezone
from typing import List

from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.accounts import UserModel
from database.models.base import Base
from database.models.movies import MovieModel


class CartModel(Base):
    """Model representing user shopping carts.

    This model stores shopping cart information for users, with a one-to-one
    relationship to users and one-to-many relationship to cart items.
    """
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="cart"
    )
    items: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="cart"
    )

    def __repr__(self) -> str:
        return f"<CartModel(id={self.id}, user_id={self.user_id})>"


class CartItemModel(Base):
    """Model representing individual items in a shopping cart.

    This model stores information about each movie item in a user's cart,
    including when it was added and relationships to the cart and movie.
    """
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc)
    )

    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )

    cart: Mapped[CartModel] = relationship(
        CartModel,
        back_populates="items"
    )
    movie: Mapped[MovieModel] = relationship(
        MovieModel,
        back_populates="cart_items"
    )

    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)

    def __repr__(self) -> str:
        return (f"<CartItemModel(id={self.id}, movie_id={self.movie_id}, "
                f"cart_id={self.cart_id}, added_at={str(self.added_at)})>")
