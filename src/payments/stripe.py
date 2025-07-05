from decimal import Decimal

import stripe
from typing import Dict, Any, Optional

from payments.interfaces import PaymentServiceInterface
from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatusEnum
from exceptions.payments import PaymentError, WebhookError


class StripePaymentService(PaymentServiceInterface):
    """Stripe payment service implementation.
    
    This class implements the PaymentServiceInterface using Stripe as the
    payment processor. It handles payment intents, refunds, webhooks, and
    checkout sessions for the Online Cinema application.
    
    The service integrates with Stripe's API to process payments, handle
    webhook events, and manage payment statuses.
    """

    def __init__(self, secret_key: str, publishable_key: str) -> None:
        """Initialize the Stripe payment service.
        
        Args:
            secret_key (str): Stripe secret key for API authentication.
            publishable_key (str): Stripe publishable key for client-side operations.
        """
        self.secret_key = secret_key
        self.publishable_key = publishable_key
        stripe.api_key = secret_key

    async def create_payment_intent(
        self,
        order: OrderModel,
        amount: Decimal,
        currency: str = "usd"
    ) -> Dict[str, Any]:
        """Create a Stripe payment intent for processing payments.
        
        Creates a payment intent with the specified amount and currency,
        including order metadata for tracking purposes.
        
        Args:
            order (OrderModel): The order to create payment intent for.
            amount (Decimal): Payment amount in the specified currency.
            currency (str): Payment currency code (default: "usd").
            
        Returns:
            Dict[str, Any]: Payment intent data including id, client_secret, amount, and currency.
            
        Raises:
            PaymentError: If payment intent creation fails.
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency,
                metadata={
                    "order_id": str(order.id),
                    "user_id": str(order.user_id)
                }
            )
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": amount,
                "currency": currency
            }
        except Exception as e:
            raise PaymentError(f"Failed to create payment intent: {str(e)}")

    async def process_payment(
        self,
        payment_intent_id: str,
        order: OrderModel,
        user_id: int
    ) -> PaymentModel:
        """Process a payment using the payment intent.
        
        Retrieves the payment intent from Stripe and creates a PaymentModel
        if the payment was successful.
        
        Args:
            payment_intent_id (str): ID of the payment intent to process.
            order (OrderModel): The order being paid for.
            user_id (int): ID of the user making the payment.
            
        Returns:
            PaymentModel: Created payment record with successful status.
            
        Raises:
            PaymentError: If payment processing fails or payment intent status is not succeeded.
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if intent.status == "succeeded":
                payment = PaymentModel(
                    user_id=user_id,
                    order_id=order.id,
                    amount=Decimal(intent.amount) / Decimal(100),
                    status=PaymentStatusEnum.SUCCESSFUL,
                    external_payment_id=payment_intent_id
                )
                return payment
            else:
                raise PaymentError(f"Payment intent status is {intent.status}")
        except Exception as e:
            raise PaymentError(f"Failed to process payment: {str(e)}")

    async def confirm_payment(self, payment_intent_id: str) -> bool:
        """Confirm a payment intent with Stripe.
        
        Args:
            payment_intent_id (str): ID of the payment intent to confirm.
            
        Returns:
            bool: True if payment was confirmed successfully.
            
        Raises:
            PaymentError: If payment confirmation fails.
        """
        try:
            intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return intent.status == "succeeded"
        except Exception as e:
            raise PaymentError(f"Failed to confirm payment: {str(e)}")

    async def cancel_payment(self, payment_intent_id: str) -> bool:
        """Cancel a payment intent with Stripe.
        
        Args:
            payment_intent_id (str): ID of the payment intent to cancel.
            
        Returns:
            bool: True if payment was cancelled successfully.
            
        Raises:
            PaymentError: If payment cancellation fails.
        """
        try:
            intent = stripe.PaymentIntent.cancel(payment_intent_id)
            return intent.status == "canceled"
        except Exception as e:
            raise PaymentError(f"Failed to cancel payment: {str(e)}")

    async def process_refund(
        self,
        payment: PaymentModel,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a refund for a payment.
        
        Creates a refund in Stripe for the specified payment. If no amount
        is specified, refunds the full payment amount.
        
        Args:
            payment (PaymentModel): The payment to refund.
            amount (Optional[Decimal]): Amount to refund (full amount if None).
            reason (Optional[str]): Reason for the refund.
            
        Returns:
            Dict[str, Any]: Refund data including id, amount, status, and reason.
            
        Raises:
            PaymentError: If refund processing fails or no external payment ID is found.
        """
        try:
            if not payment.external_payment_id:
                raise PaymentError("No external payment ID found")

            refund_data = {
                "payment_intent": payment.external_payment_id,
            }

            if amount:
                refund_data["amount"] = int(amount * 100)

            if reason:
                refund_data["reason"] = reason

            refund = stripe.Refund.create(**refund_data)

            return {
                "id": refund.id,
                "amount": refund.amount / 100,
                "status": refund.status,
                "reason": refund.reason
            }
        except Exception as e:
            raise PaymentError(f"Failed to process refund: {str(e)}")

    async def handle_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Handle webhook events from Stripe.
        
        Processes incoming webhook events from Stripe, validates the signature,
        and routes events to appropriate handlers.
        
        Args:
            payload (bytes): Raw webhook payload from Stripe.
            signature (str): Webhook signature for verification.
            
        Returns:
            Dict[str, Any]: Processed webhook event data.
            
        Raises:
            WebhookError: If webhook signature is invalid or payload is malformed.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.secret_key
            )

            if event.type == "payment_intent.succeeded":
                return await self._handle_payment_succeeded(event.data.object)
            elif event.type == "payment_intent.payment_failed":
                return await self._handle_payment_failed(event.data.object)
            elif event.type == "charge.refunded":
                return await self._handle_refund_processed(event.data.object)
            else:
                return {"status": "ignored", "event_type": event.type}

        except ValueError as e:
            raise WebhookError(f"Invalid payload: {str(e)}")
        except Exception as e:
            raise WebhookError(f"Invalid signature: {str(e)}")

    async def _handle_payment_succeeded(
        self,
        payment_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle payment succeeded webhook event.
        
        Args:
            payment_intent (Dict[str, Any]): Payment intent data from webhook.
            
        Returns:
            Dict[str, Any]: Processed event data.
        """
        return {
            "status": "processed",
            "event_type": "payment_intent.succeeded",
            "payment_intent_id": payment_intent["id"]
        }

    async def _handle_payment_failed(
        self,
        payment_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle payment failed webhook event.
        
        Args:
            payment_intent (Dict[str, Any]): Payment intent data from webhook.
            
        Returns:
            Dict[str, Any]: Processed event data.
        """
        return {
            "status": "processed",
            "event_type": "payment_intent.payment_failed",
            "payment_intent_id": payment_intent["id"]
        }

    async def _handle_refund_processed(
        self,
        charge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle refund processed webhook event.
        
        Args:
            charge (Dict[str, Any]): Charge data from webhook.
            
        Returns:
            Dict[str, Any]: Processed event data.
        """
        return {
            "status": "processed",
            "event_type": "charge.refunded",
            "charge_id": charge["id"]
        }

    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> PaymentStatusEnum:
        """Get the current status of a payment from Stripe.
        
        Args:
            payment_intent_id (str): ID of the payment intent.
            
        Returns:
            PaymentStatusEnum: Current payment status.
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if intent.status == "succeeded":
                return PaymentStatusEnum.SUCCESSFUL
            elif intent.status == "canceled":
                return PaymentStatusEnum.CANCELED
            else:
                return PaymentStatusEnum.SUCCESSFUL
        except Exception:
            return PaymentStatusEnum.CANCELED

    async def validate_payment_method(self, payment_method_id: str) -> bool:
        """Validate a payment method with Stripe.
        
        Args:
            payment_method_id (str): ID of the payment method to validate.
            
        Returns:
            bool: True if payment method is valid and exists.
        """
        try:
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            return True
        except Exception:
            return False

    async def create_checkout_session(
        self,
        order: OrderModel,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session for payment.
        
        Creates a checkout session with line items for each movie in the order,
        allowing customers to complete payment through Stripe's hosted checkout.
        
        Args:
            order (OrderModel): The order for checkout session.
            success_url (str): URL to redirect on successful payment.
            cancel_url (str): URL to redirect on cancelled payment.
            
        Returns:
            Dict[str, Any]: Checkout session data including id, url, and amount_total.
            
        Raises:
            PaymentError: If checkout session creation fails.
        """
        try:
            line_items = []
            for item in order.items:
                line_items.append(
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": item.movie.name,
                            },
                            "unit_amount": int(item.price_at_order * 100),
                        },
                        "quantity": 1,
                    }
                )

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "order_id": str(order.id),
                    "user_id": str(order.user_id)
                }
            )

            amount_total = session.amount_total
            if amount_total is not None:
                amount_total = amount_total / 100

            return {
                "id": session.id,
                "url": session.url,
                "amount_total": amount_total
            }
        except Exception as e:
            raise PaymentError(f"Failed to create checkout session: {str(e)}")

    async def retrieve_payment_intent(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """Retrieve payment intent details from Stripe.
        
        Args:
            payment_intent_id (str): ID of the payment intent.
            
        Returns:
            Dict[str, Any]: Payment intent details including id, status, amount, currency, and metadata.
            
        Raises:
            PaymentError: If payment intent retrieval fails.
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "id": intent.id,
                "status": intent.status,
                "amount": intent.amount / 100,
                "currency": intent.currency,
                "metadata": intent.metadata
            }
        except Exception as e:
            raise PaymentError(f"Failed to retrieve payment intent: {str(e)}")

    async def update_payment_status(
        self,
        payment: PaymentModel,
        new_status: PaymentStatusEnum,
        external_payment_id: Optional[str] = None
    ) -> PaymentModel:
        """Update the status of a payment.
        
        Updates the payment status and optionally sets the external payment ID.
        
        Args:
            payment (PaymentModel): The payment to update.
            new_status (PaymentStatusEnum): New payment status.
            external_payment_id (Optional[str]): External payment ID from Stripe.
            
        Returns:
            PaymentModel: Updated payment record.
        """
        payment.status = new_status
        if external_payment_id:
            payment.external_payment_id = hash(external_payment_id) % (2 ** 31)
        return payment

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify webhook signature for security.
        
        Validates that the webhook payload was sent by Stripe using the
        webhook signature.
        
        Args:
            payload (bytes): Raw webhook payload.
            signature (str): Webhook signature to verify.
            
        Returns:
            bool: True if signature is valid.
        """
        try:
            stripe.Webhook.construct_event(payload, signature, self.secret_key)
            return True
        except (ValueError, Exception):
            return False
