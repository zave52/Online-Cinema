from decimal import Decimal
from typing import List, Dict, Any
from pydantic import EmailStr


class StubEmailSender:
    """Stub implementation of EmailSender for testing.

    This class captures all email sending calls for verification in tests.
    """

    def __init__(self):
        """Initialize the stub with empty sent emails list."""
        self.sent_emails: List[Dict[str, Any]] = []
        self.call_count = 0

    def clear_sent_emails(self) -> None:
        """Clear the list of sent emails."""
        self.sent_emails.clear()
        self.call_count = 0

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Get all sent emails."""
        return self.sent_emails.copy()

    def get_sent_emails_by_recipient(self, email: str) -> List[Dict[str, Any]]:
        """Get sent emails for a specific recipient."""
        return [email_data for email_data in self.sent_emails
                if email_data.get('recipient') == email]

    def get_sent_emails_by_type(self, email_type: str) -> List[Dict[str, Any]]:
        """Get sent emails by type."""
        return [email_data for email_data in self.sent_emails
                if email_data.get('type') == email_type]

    async def send_activation_email(
        self,
        email: EmailStr,
        activation_link: str
    ) -> None:
        """Record activation email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'activation',
            'recipient': str(email),
            'activation_link': activation_link,
            'subject': 'Account Activation'
        })

    async def send_activation_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ) -> None:
        """Record activation complete email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'activation_complete',
            'recipient': str(email),
            'login_link': login_link,
            'subject': 'Account Activation Successfully'
        })

    async def send_password_reset_email(
        self,
        email: EmailStr,
        password_reset_link: str
    ) -> None:
        """Record password reset email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'password_reset',
            'recipient': str(email),
            'reset_link': password_reset_link,
            'subject': 'Password Reset Request'
        })

    async def send_password_reset_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ) -> None:
        """Record password reset complete email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'password_reset_complete',
            'recipient': str(email),
            'login_link': login_link,
            'subject': 'Password Reset Complete'
        })

    async def send_password_changed_email(self, email: EmailStr) -> None:
        """Record password changed email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'password_changed',
            'recipient': str(email),
            'subject': 'Password Change Successfully'
        })

    async def send_comment_reply_notification_email(
        self,
        email: EmailStr,
        comment_id: int,
        reply_text: str,
        reply_author: EmailStr
    ) -> None:
        """Record comment reply notification email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'comment_reply',
            'recipient': str(email),
            'comment_id': comment_id,
            'reply_text': reply_text,
            'reply_author': str(reply_author),
            'subject': 'New Reply to Your Comment'
        })

    async def send_refund_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Record refund confirmation email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'refund_confirmation',
            'recipient': str(email),
            'order_id': order_id,
            'amount': str(amount),
            'subject': 'Refund Confirmation'
        })

    async def send_payment_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Record payment confirmation email sending."""
        self.call_count += 1
        self.sent_emails.append({
            'type': 'payment_confirmation',
            'recipient': str(email),
            'order_id': order_id,
            'amount': str(amount),
            'subject': 'Payment Confirmation'
        })
