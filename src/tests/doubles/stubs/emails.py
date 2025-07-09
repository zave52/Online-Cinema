from decimal import Decimal
from typing import List

from pydantic import EmailStr

from notifications.interfaces import EmailSenderInterface


class StubEmailSender(EmailSenderInterface):
    """Stub email sender for testing that doesn't actually send emails."""

    def __init__(self):
        self.sent_emails = []

    async def send_activation_email(
        self,
        email: str,
        activation_link: str
    ) -> None:
        """Simulate sending activation email."""
        self.sent_emails.append(
            {
                "type": "activation",
                "to": email,
                "activation_link": activation_link
            }
        )

    async def send_password_reset_email(
        self,
        email: str,
        reset_link: str
    ) -> None:
        """Simulate sending password reset email."""
        self.sent_emails.append(
            {
                "type": "password_reset",
                "to": email,
                "reset_link": reset_link
            }
        )

    async def send_activation_complete_email(
        self,
        email: str,
        login_link: str
    ) -> None:
        """Simulate sending activation complete email."""
        self.sent_emails.append(
            {
                "type": "activation_complete",
                "to": email,
                "login_link": login_link
            }
        )

    async def send_password_reset_complete_email(
        self,
        email: str,
        login_link: str
    ) -> None:
        """Simulate sending password reset complete email."""
        self.sent_emails.append(
            {
                "type": "password_reset_complete",
                "to": email,
                "login_link": login_link
            }
        )

    async def send_password_changed_email(self, email: str) -> None:
        """Simulate sending password changed email."""
        self.sent_emails.append(
            {
                "type": "password_changed",
                "to": email
            }
        )

    async def send_comment_reply_notification_email(
        self,
        email: EmailStr,
        comment_id: int,
        reply_text: str,
        reply_author: EmailStr
    ) -> None:
        """Simulate sending comment reply notification email."""
        self.sent_emails.append(
            {
                "type": "comment_reply_notification",
                "to": email,
                "comment_id": comment_id,
                "reply_text": reply_text,
                "reply_author": reply_author
            }
        )

    async def send_payment_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Simulate sending payment confirmation email."""
        self.sent_emails.append(
            {
                "type": "payment_confirmation",
                "to": email,
                "order_id": order_id,
                "amount": amount
            }
        )

    async def send_refund_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Simulate sending refund confirmation email."""
        self.sent_emails.append(
            {
                "type": "refund_confirmation",
                "to": email,
                "order_id": order_id,
                "amount": amount
            }
        )

    def get_sent_emails(self) -> List[dict]:
        """Get all sent emails for testing verification."""
        return self.sent_emails

    def clear_sent_emails(self) -> None:
        """Clear sent emails list."""
        self.sent_emails.clear()
