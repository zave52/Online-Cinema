from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import uuid4

from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatusEnum
from exceptions.payments import PaymentError
from payments.interfaces import PaymentServiceInterface


class FakePaymentService(PaymentServiceInterface):
    """Fake payment service implementation for testing.

    This class provides a test-friendly implementation of the PaymentServiceInterface
    that simulates payment processing without making actual API calls to payment providers.
    """

    def __init__(self):
        """Initialize the fake payment service."""
        self._payment_intents = {}
        self._processed_intents = set()

    async def create_payment_intent(
        self,
        order: OrderModel,
        amount: Decimal,
        currency: str = "usd"
    ) -> Dict[str, Any]:
        """Create a fake payment intent for testing.

        Args:
            order (OrderModel): The order to create payment intent for.
            amount (Decimal): Payment amount.
            currency (str): Payment currency code.

        Returns:
            Dict[str, Any]: Fake payment intent data.
        """
        intent_id = f"pi_test_{uuid4().hex[:16]}"
        client_secret = f"{intent_id}_secret_{uuid4().hex[:16]}"

        self._payment_intents[intent_id] = {
            "id": intent_id,
            "client_secret": client_secret,
            "amount": int(amount * 100),
            "currency": currency,
            "status": "requires_payment_method",
            "metadata": {
                "order_id": str(order.id),
                "user_id": str(order.user_id)
            }
        }

        return {
            "id": intent_id,
            "client_secret": client_secret,
            "amount": amount,
            "currency": currency
        }

    async def retrieve_payment_intent(self, payment_intent_id: str) -> Dict[
        str, Any]:
        """Retrieve a fake payment intent.

        Args:
            payment_intent_id (str): ID of the payment intent.

        Returns:
            Dict[str, Any]: Payment intent data.

        Raises:
            PaymentError: If payment intent not found.
        """
        if payment_intent_id not in self._payment_intents:
            raise PaymentError(f"Payment intent {payment_intent_id} not found")

        intent = self._payment_intents[payment_intent_id].copy()

        if payment_intent_id not in self._processed_intents:
            intent["status"] = "succeeded"

        intent["amount"] = Decimal(intent["amount"]) / 100

        return intent

    async def process_payment(
        self,
        payment_intent_id: str,
        order: OrderModel,
        user_id: int
    ) -> PaymentModel:
        """Process a fake payment.

        Args:
            payment_intent_id (str): ID of the payment intent.
            order (OrderModel): The order being paid for.
            user_id (int): ID of the user making the payment.

        Returns:
            PaymentModel: Created payment record.

        Raises:
            PaymentError: If payment processing fails.
        """
        intent = await self.retrieve_payment_intent(payment_intent_id)

        if payment_intent_id in self._processed_intents:
            raise PaymentError("Payment intent has already been processed")

        if intent["status"] != "succeeded":
            raise PaymentError(
                f"Payment intent status is {intent['status']}, expected 'succeeded'"
            )

        self._processed_intents.add(payment_intent_id)

        amount = Decimal(str(intent["amount"]))

        payment = PaymentModel(
            user_id=user_id,
            order_id=order.id,
            amount=amount,
            status=PaymentStatusEnum.SUCCESSFUL,
            external_payment_id=payment_intent_id
        )

        return payment

    async def confirm_payment(self, payment_intent_id: str) -> bool:
        """Confirm a fake payment intent.

        Args:
            payment_intent_id (str): ID of the payment intent to confirm.

        Returns:
            bool: True if payment was confirmed successfully.
        """
        if payment_intent_id in self._payment_intents:
            self._payment_intents[payment_intent_id]["status"] = "succeeded"
            return True
        return False

    async def cancel_payment(self, payment_intent_id: str) -> bool:
        """Cancel a fake payment intent.

        Args:
            payment_intent_id (str): ID of the payment intent to cancel.

        Returns:
            bool: True if payment was cancelled successfully.
        """
        if payment_intent_id in self._payment_intents:
            self._payment_intents[payment_intent_id]["status"] = "canceled"
            return True
        return False

    async def process_refund(
        self,
        payment: PaymentModel,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a fake refund.

        Args:
            payment (PaymentModel): The payment to refund.
            amount (Optional[Decimal]): Amount to refund.
            reason (Optional[str]): Reason for the refund.

        Returns:
            Dict[str, Any]: Fake refund data.
        """
        refund_amount = amount or payment.amount
        refund_id = f"re_test_{uuid4().hex[:16]}"

        return {
            "id": refund_id,
            "amount": refund_amount,
            "status": "succeeded",
            "reason": reason or "requested_by_customer"
        }

    async def handle_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Handle a fake webhook event.

        Args:
            payload (bytes): Webhook payload.
            signature (str): Webhook signature.

        Returns:
            Dict[str, Any]: Fake webhook event data.
        """
        return {
            "id": f"evt_test_{uuid4().hex[:16]}",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": f"pi_test_{uuid4().hex[:16]}",
                    "status": "succeeded"
                }
            }
        }

    async def create_checkout_session(
        self,
        order: OrderModel,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a fake checkout session.

        Args:
            order (OrderModel): The order to create checkout session for.
            success_url (str): URL to redirect to on success.
            cancel_url (str): URL to redirect to on cancel.

        Returns:
            Dict[str, Any]: Fake checkout session data.
        """
        session_id = f"cs_test_{uuid4().hex[:16]}"

        # Calculate amount_total from order items to match Stripe behavior
        amount_total = Decimal('0')
        for item in order.items:
            amount_total += item.price_at_order

        return {
            "id": session_id,
            "url": f"https://checkout.stripe.com/pay/{session_id}",
            "amount_total": amount_total
        }

    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> PaymentStatusEnum:
        """Get the current status of a fake payment.

        Args:
            payment_intent_id (str): ID of the payment intent.

        Returns:
            PaymentStatusEnum: Current payment status.
        """
        if payment_intent_id in self._processed_intents:
            return PaymentStatusEnum.SUCCESSFUL
        elif payment_intent_id in self._payment_intents:
            intent = self._payment_intents[payment_intent_id]
            if intent["status"] == "canceled":
                return PaymentStatusEnum.CANCELED
            else:
                return PaymentStatusEnum.SUCCESSFUL
        else:
            return PaymentStatusEnum.CANCELED

    async def validate_payment_method(self, payment_method_id: str) -> bool:
        """Validate a fake payment method.

        Args:
            payment_method_id (str): ID of the payment method to validate.

        Returns:
            bool: True if payment method is valid.
        """
        # For testing, consider all payment methods valid unless they contain "invalid"
        return "invalid" not in payment_method_id.lower()

    async def update_payment_status(
        self,
        payment: PaymentModel,
        new_status: PaymentStatusEnum,
        external_payment_id: Optional[str] = None
    ) -> PaymentModel:
        """Update the status of a fake payment.

        Args:
            payment (PaymentModel): The payment to update.
            new_status (PaymentStatusEnum): New payment status.
            external_payment_id (Optional[str]): External payment ID from provider.

        Returns:
            PaymentModel: Updated payment record.
        """
        payment.status = new_status
        if external_payment_id:
            payment.external_payment_id = external_payment_id
        return payment

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify fake webhook signature for security.

        Args:
            payload (bytes): Webhook payload.
            signature (str): Webhook signature.

        Returns:
            bool: True if signature is valid (always true for testing).
        """
        return "invalid" not in signature.lower()
