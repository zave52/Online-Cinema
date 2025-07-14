from decimal import Decimal

from pydantic import EmailStr

from notifications.interfaces import EmailSenderInterface


class StubEmailSender(EmailSenderInterface):
    """Stub implementation of EmailSender for testing.

    This class captures all email sending calls for verification in tests.
    """

    async def send_activation_email(
        self,
        email: EmailStr,
        activation_link: str
    ) -> None:
        """Sends an activation email to the user.

        Args:
            email: The recipient's email address.
            activation_link: The link to activate the user's account.
        """
        pass

    async def send_activation_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ) -> None:
        """Sends an email confirming successful account activation.

        Args:
            email: The recipient's email address.
            login_link: The link to the login page.
        """
        pass

    async def send_password_reset_email(
        self,
        email: EmailStr,
        password_reset_link: str
    ) -> None:
        """Sends a password reset email to the user.

        Args:
            email: The recipient's email address.
            password_reset_link: The link to reset the user's password.
        """
        pass

    async def send_password_reset_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ) -> None:
        """Sends an email confirming successful password reset.

        Args:
            email: The recipient's email address.
            login_link: The link to the login page.
        """
        pass

    async def send_password_changed_email(self, email: EmailStr) -> None:
        """Sends an email confirming that the user's password has been changed.

        Args:
            email: The recipient's email address.
        """
        pass

    async def send_comment_reply_notification_email(
        self,
        email: EmailStr,
        comment_id: int,
        reply_text: str,
        reply_author: EmailStr
    ) -> None:
        """Sends an email notifying the user about a reply to their comment.

        Args:
            email: The recipient's email address.
            comment_id: The ID of the comment that was replied to.
            reply_text: The text of the reply.
            reply_author: The email address of the reply author.
        """
        pass

    async def send_refund_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Sends an email confirming a refund.

        Args:
            email: The recipient's email address.
            order_id: The ID of the refunded order.
            amount: The refunded amount.
        """
        pass

    async def send_payment_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: Decimal
    ) -> None:
        """Sends an email confirming a successful payment.

        Args:
            email: The recipient's email address.
            order_id: The ID of the paid order.
            amount: The paid amount.
        """
        pass
