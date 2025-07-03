from abc import ABC, abstractmethod
from decimal import Decimal

from pydantic import EmailStr


class EmailSenderInterface(ABC):
    @abstractmethod
    async def send_activation_email(
        self,
        email: EmailStr,
        activation_link: str
    ) -> None:
        pass

    @abstractmethod
    async def send_activation_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ) -> None:
        pass

    @abstractmethod
    async def send_password_reset_email(
        self,
        email: EmailStr,
        password_reset_link: str
    ) -> None:
        pass

    @abstractmethod
    async def send_password_reset_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ):
        pass

    @abstractmethod
    async def send_password_changed_email(
        self,
        email: EmailStr
    ) -> None:
        pass

    @abstractmethod
    async def send_comment_reply_notification_email(
        self,
        email: EmailStr,
        comment_id: int,
        reply_text: str,
        reply_author: EmailStr
    ) -> None:
        pass

    @abstractmethod
    async def send_refund_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        pass

    @abstractmethod
    async def send_payment_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        pass
