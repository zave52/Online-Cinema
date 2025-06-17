from abc import ABC, abstractmethod

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
