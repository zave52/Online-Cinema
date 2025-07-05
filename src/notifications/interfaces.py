from abc import ABC, abstractmethod
from decimal import Decimal

from pydantic import EmailStr


class EmailSenderInterface(ABC):
    """Abstract interface for email notification services.
    
    This interface defines the contract for sending various types of email
    notifications including account activation, password reset, payment
    confirmations, and comment notifications.
    """

    @abstractmethod
    async def send_activation_email(
        self,
        email: EmailStr,
        activation_link: str
    ) -> None:
        """Send account activation email to new users.
        
        Args:
            email (EmailStr): Recipient's email address.
            activation_link (str): Link for account activation.
        """
        pass

    @abstractmethod
    async def send_activation_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ) -> None:
        """Send confirmation email when account activation is complete.
        
        Args:
            email (EmailStr): Recipient's email address.
            login_link (str): Link to login page.
        """
        pass

    @abstractmethod
    async def send_password_reset_email(
        self,
        email: EmailStr,
        password_reset_link: str
    ) -> None:
        """Send password reset email with reset link.
        
        Args:
            email (EmailStr): Recipient's email address.
            password_reset_link (str): Link for password reset.
        """
        pass

    @abstractmethod
    async def send_password_reset_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ) -> None:
        """Send confirmation email when password reset is complete.
        
        Args:
            email (EmailStr): Recipient's email address.
            login_link (str): Link to login page.
        """
        pass

    @abstractmethod
    async def send_password_changed_email(
        self,
        email: EmailStr
    ) -> None:
        """Send confirmation email when password is changed successfully.
        
        Args:
            email (EmailStr): Recipient's email address.
        """
        pass

    @abstractmethod
    async def send_comment_reply_notification_email(
        self,
        email: EmailStr,
        comment_id: int,
        reply_text: str,
        reply_author: EmailStr
    ) -> None:
        """Send notification email when someone replies to a user's comment.
        
        Args:
            email (EmailStr): Recipient's email address.
            comment_id (int): ID of the original comment.
            reply_text (str): Text of the reply.
            reply_author (EmailStr): Email of the person who replied.
        """
        pass

    @abstractmethod
    async def send_refund_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Send confirmation email when a refund is processed.
        
        Args:
            email (EmailStr): Recipient's email address.
            order_id (int): ID of the order being refunded.
            amount (Decimal): Amount being refunded.
        """
        pass

    @abstractmethod
    async def send_payment_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Send confirmation email when a payment is processed successfully.
        
        Args:
            email (EmailStr): Recipient's email address.
            order_id (int): ID of the order being paid for.
            amount (Decimal): Amount paid.
        """
        pass
