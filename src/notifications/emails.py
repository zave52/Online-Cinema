from pydantic import EmailStr
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

from notifications.interfaces import EmailSenderInterface


class EmailSender(FastMail, EmailSenderInterface):
    def __init__(self, config: ConnectionConfig) -> None:
        super().__init__(config=config)

    async def send_activation_email(
        self,
        email: EmailStr,
        activation_link: str
    ) -> None:
        message = MessageSchema(
            recipients=[email],
            subject="Account Activation",
            subtype=MessageType.html,
            template_body=[activation_link]
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
        message = MessageSchema(
            recipients=[email],
            subject="Account Activation Successfully",
            subtype=MessageType.html,
            template_body=[login_link]
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
        message = MessageSchema(
            recipients=[email],
            subject="Password Reset Request",
            subtype=MessageType.html,
            template_body=[password_reset_link]
        )

        await self.send_message(
            message=message,
            template_name="password_reset_request.html"
        )

    async def send_password_reset_complete_email(
        self,
        email: EmailStr,
        login_link: str
    ):
        message = MessageSchema(
            recipients=[email],
            subject="Password Reset Complete",
            subtype=MessageType.html,
            template_body=[login_link]
        )

        await self.send_message(
            message=message,
            template_name="password_reset_complete.html"
        )

    async def send_password_changed_email(self, email: EmailStr) -> None:
        message = MessageSchema(
            recipients=[email],
            subject="Password Change Successfully",
            subtype=MessageType.html
        )

        await self.send_message(
            message=message,
            template_name="password_change_successfully"
        )

    async def send_comment_reply_notification_email(
        self,
        email: EmailStr,
        comment_id: int,
        reply_text: str,
        reply_author: EmailStr
    ) -> None:
        message = MessageSchema(
            recipients=[email],
            subject="New Reply to Your Comment",
            subtype=MessageType.html,
            template_body=[comment_id, reply_text, reply_author]
        )

        await self.send_message(
            message=message,
            template_name="comment_reply_notification.html"
        )

    async def send_refund_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: float
    ) -> None:
        message = MessageSchema(
            recipients=[email],
            subject="Refund Confirmation",
            subtype=MessageType.html,
            template_body=[order_id, amount]
        )

        await self.send_message(
            message=message,
            template_name="refund_confirmation_email.html"
        )

    async def send_payment_confirmation_email(
        self,
        email: EmailStr,
        order_id: int,
        amount: float
    ) -> None:
        message = MessageSchema(
            recipients=[email],
            subject="Payment Confirmation",
            subtype=MessageType.html,
            template_body=[order_id, amount]
        )

        await self.send_message(
            message=message,
            template_name="payment_confirmation.html"
        )
