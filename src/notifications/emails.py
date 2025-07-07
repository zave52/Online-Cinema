from decimal import Decimal

from pydantic import EmailStr
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

from notifications.interfaces import EmailSenderInterface


class EmailSender(FastMail, EmailSenderInterface):
    """Email sender service for sending various types of notifications.
    
    This class extends FastMail to provide specific email templates for
    different types of notifications like account activation, password reset,
    payment confirmations, etc.
    """
    
    def __init__(self, config: ConnectionConfig) -> None:
        """Initialize the email sender with connection configuration.
        
        Args:
            config (ConnectionConfig): Email server configuration.
        """
        super().__init__(config=config)

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
        message = MessageSchema(
            recipients=[email],
            subject="Account Activation",
            subtype=MessageType.html,
            template_body={
                "email": email,
                "activation_link": activation_link}
        )

        await self.send_message(
            message=message,
            template_name="activation_request.html"
        )

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
        message = MessageSchema(
            recipients=[email],
            subject="Account Activation Successfully",
            subtype=MessageType.html,
            template_body={
                "email": email,
                "login_link": login_link
            }
        )

        await self.send_message(
            message=message,
            template_name="activation_complete.html"
        )

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
        message = MessageSchema(
            recipients=[email],
            subject="Password Reset Request",
            subtype=MessageType.html,
            template_body={
                "email": email,
                "password_reset_link": password_reset_link
            }
        )

        await self.send_message(
            message=message,
            template_name="password_reset_request.html"
        )

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
        message = MessageSchema(
            recipients=[email],
            subject="Password Reset Complete",
            subtype=MessageType.html,
            template_body={
                "email": email,
                "login_link": login_link
            }
        )

        await self.send_message(
            message=message,
            template_name="password_reset_complete.html"
        )

    async def send_password_changed_email(self, email: EmailStr) -> None:
        """Send confirmation email when password is changed successfully.
        
        Args:
            email (EmailStr): Recipient's email address.
        """
        message = MessageSchema(
            recipients=[email],
            subject="Password Change Successfully",
            subtype=MessageType.html,
            template_body={"email": email}
        )

        await self.send_message(
            message=message,
            template_name="password_change_successfully.html"
        )

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
        message = MessageSchema(
            recipients=[email],
            subject="New Reply to Your Comment",
            subtype=MessageType.html,
            template_body={
                "comment_id": comment_id,
                "reply_text": reply_text,
                "reply_author": reply_author
            }
        )

        await self.send_message(
            message=message,
            template_name="comment_reply_notification.html"
        )

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
        message = MessageSchema(
            recipients=[email],
            subject="Refund Confirmation",
            subtype=MessageType.html,
            template_body={
                "order_id": order_id,
                "amount": amount
            }
        )

        await self.send_message(
            message=message,
            template_name="refund_confirmation_email.html"
        )

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
        message = MessageSchema(
            recipients=[email],
            subject="Payment Confirmation",
            subtype=MessageType.html,
            template_body={
                "order_id": order_id,
                "amount": amount
            }
        )

        await self.send_message(
            message=message,
            template_name="payment_confirmation.html"
        )
