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

    def __init__(
        self,
        secret_key: str = "sk_test_123",
        publishable_key: str = "pk_test_123"
    ):
        """Initialize the fake payment service."""
        self.secret_key = secret_key
        self.publishable_key = publishable_key
        self._payment_intents: dict[str, Any] = {}
        self._payment_methods: dict[str, Any] = {}
        self._processed_intents: set[str] = set()
        self._refunds: dict[str, Any] = {}

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
            "payment_method": None,
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
            PaymentError: If payment intent not found or already processed.
        """
        if payment_intent_id not in self._payment_intents:
            raise PaymentError(f"Payment intent {payment_intent_id} not found")

        intent = self._payment_intents[payment_intent_id]

        if intent["status"] != "requires_confirmation":
            raise PaymentError(f"Payment intent status is {intent['status']}")

        payment = PaymentModel(
            user_id=user_id,
            order_id=order.id,
            amount=Decimal(intent["amount"]) / 100,
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

        Raises:
            PaymentError: If payment intent not found.
        """
        if payment_intent_id not in self._payment_intents:
            raise PaymentError(f"Payment intent {payment_intent_id} not found")

        self._payment_intents[payment_intent_id]["status"] = "succeeded"
        return True

    async def cancel_payment(self, payment_intent_id: str) -> bool:
        """Cancel a fake payment intent.

        Args:
            payment_intent_id (str): ID of the payment intent to cancel.

        Returns:
            bool: True if payment was cancelled successfully.

        Raises:
            PaymentError: If payment intent not found.
        """
        if payment_intent_id not in self._payment_intents:
            raise PaymentError(f"Payment intent {payment_intent_id} not found")

        self._payment_intents[payment_intent_id]["status"] = "canceled"
        return True

    async def process_refund(
        self,
        payment: PaymentModel,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a fake refund.

        Args:
            payment (PaymentModel): The payment to refund.
            amount (Optional[Decimal]): Amount to refund (full amount if None).
            reason (Optional[str]): Reason for the refund.

        Returns:
            Dict[str, Any]: Fake refund data.
        """
        if not payment.external_payment_id:
            raise PaymentError("No external payment ID found")

        refund_amount = amount or payment.amount
        refund_id = f"re_test_{uuid4().hex[:16]}"

        self._refunds[refund_id] = {
            "id": refund_id,
            "payment_intent": payment.external_payment_id,
            "amount": int(refund_amount * 100),
            "status": "succeeded",
            "reason": reason or "requested_by_customer"
        }

        return {
            "id": refund_id,
            "amount": refund_amount,
            "status": "succeeded",
            "reason": reason or "requested_by_customer"
        }

    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
        db: Any,
        email_sender: Any
    ) -> Dict[str, Any]:
        """Handle fake webhook events.

        Args:
            payload (bytes): Raw webhook payload.
            signature (str): Webhook signature for verification.

        Returns:
            Dict[str, Any]: Processed webhook event data.
        """
        # In a real scenario, you would parse the payload and signature
        # to determine the event type and data.
        # For this fake service, we'll just return a mock response.
        return {
            "status": "processed",
            "event_type": "payment_intent.succeeded",
            "payment_intent_id": "pi_test_fake"
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
        if payment_intent_id not in self._payment_intents:
            return PaymentStatusEnum.CANCELED

        intent = self._payment_intents[payment_intent_id]

        if intent["status"] == "succeeded":
            return PaymentStatusEnum.SUCCESSFUL
        elif intent["status"] == "canceled":
            return PaymentStatusEnum.CANCELED
        else:
            return PaymentStatusEnum.REFUNDED

    async def validate_payment_method(self, payment_method_id: str) -> bool:
        """Validate a fake payment method.

        Args:
            payment_method_id (str): ID of the payment method to validate.

        Returns:
            bool: True if payment method is valid and exists.
        """
        return payment_method_id in self._payment_methods

    async def create_checkout_session(
        self,
        order: OrderModel,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a fake checkout session.

        Args:
            order (OrderModel): The order for checkout session.
            success_url (str): URL to redirect on successful payment.
            cancel_url (str): URL to redirect on cancelled payment.

        Returns:
            Dict[str, Any]: Fake checkout session data.
        """
        session_id = f"cs_test_{uuid4().hex[:16]}"
        amount_total = sum(item.price_at_order for item in order.items)

        return {
            "id": session_id,
            "url": f"https://checkout.stripe.com/pay/{session_id}",
            "amount_total": float(amount_total)
        }

    async def retrieve_payment_intent(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
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
        intent["amount"] = Decimal(intent["amount"]) / 100
        return intent

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
            payload (bytes): Raw webhook payload.
            signature (str): Webhook signature to verify.

        Returns:
            bool: True if signature is valid (always True for fake).
        """
        return True

    def create_payment_method(
        self,
        payment_method_type: str = "card",
        card_number: str = "4242424242424242",
        exp_month: int = 12,
        exp_year: int = 2025,
        cvc: str = "123"
    ) -> Dict[str, Any]:
        """Create a fake payment method for testing.

        Args:
            payment_method_type (str): Type of payment method (default: "card").
            card_number (str): Card number for testing.
            exp_month (int): Card expiration month.
            exp_year (int): Card expiration year.
            cvc (str): Card CVC code.

        Returns:
            Dict[str, Any]: Fake payment method data.
        """
        method_id = f"pm_test_{uuid4().hex[:16]}"

        brand = "visa"
        if card_number.startswith("5"):
            brand = "mastercard"
        elif card_number.startswith("34") or card_number.startswith("37"):
            brand = "amex"

        payment_method = {
            "id": method_id,
            "type": payment_method_type,
            "card": {
                "brand": brand,
                "last4": card_number[-4:],
                "exp_month": exp_month,
                "exp_year": exp_year,
            }
        }

        self._payment_methods[method_id] = payment_method

        return payment_method

    def attach_payment_method_to_intent(
        self,
        payment_intent_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Attach a payment method to a payment intent.

        Args:
            payment_intent_id (str): ID of the payment intent.
            payment_method_id (str): ID of the payment method to attach.

        Returns:
            Dict[str, Any]: Updated payment intent data.

        Raises:
            PaymentError: If payment intent or method not found.
        """
        if payment_intent_id not in self._payment_intents:
            raise PaymentError(f"Payment intent {payment_intent_id} not found")

        if payment_method_id not in self._payment_methods:
            raise PaymentError(f"Payment method {payment_method_id} not found")

        self._payment_intents[payment_intent_id][
            "payment_method"] = payment_method_id
        self._payment_intents[payment_intent_id][
            "status"] = "requires_confirmation"

        return {
            "id": payment_intent_id,
            "status": "requires_confirmation",
            "payment_method": payment_method_id
        }
