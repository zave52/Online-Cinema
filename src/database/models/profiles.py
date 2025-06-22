from datetime import date
from typing import Optional

from sqlalchemy import Integer, String, Enum as SqlEnum, Date, Text, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database.models.accounts import GenderEnum, UserModel
from database.models.base import Base


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[GenderEnum]] = mapped_column(SqlEnum(GenderEnum))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    info: Mapped[Optional[str]] = mapped_column(Text)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="profile",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<UserModel(id={self.id}, first_name={self.first_name}, "
            f"last_name={self.last_name}, gender={self.gender}, "
            f"date_of_birth={self.date_of_birth})>"
        )
