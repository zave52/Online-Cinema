import stripe
from typing import Dict, Any, Optional, List
from decimal import Decimal

from payments.interfaces import PaymentServiceInterface
from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatusEnum
from exceptions.payments import PaymentError, WebhookError


class StripePaymentService(PaymentServiceInterface):
    def __init__(self, secret_key: str, publishable_key: str) -> None:
        self.secret_key = secret_key
        self.publishable_key = publishable_key
        stripe.api_key = secret_key

    async def create_payment_intent(
        self,
        order: OrderModel,
        amount: Decimal,
        currency: str = "usd"
    ) -> Dict[str, Any]:
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
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if intent.status == "succeeded":
                payment = PaymentModel(
                    user_id=user_id,
                    order_id=order.id,
                    amount=Decimal(intent.amount) / 100,
                    status=PaymentStatusEnum.SUCCESSFUL,
                    external_payment_id=None
                )
                return payment
            else:
                raise PaymentError(f"Payment intent status is {intent.status}")
        except Exception as e:
            raise PaymentError(f"Failed to process payment: {str(e)}")

    async def confirm_payment(self, payment_intent_id: str) -> bool:
        try:
            intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return intent.status == "succeeded"
        except Exception as e:
            raise PaymentError(f"Failed to confirm payment: {str(e)}")

    async def cancel_payment(self, payment_intent_id: str) -> bool:
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
        try:
            if not payment.external_payment_id:
                raise PaymentError("No external payment ID found")

            refund_data = {
                "payment_intent": str(payment.external_payment_id),
                "reason": reason or "requested_by_customer"
            }

            if amount:
                refund_data["amount"] = int(amount * 100)

            refund = stripe.Refund.create(**refund_data)

            return {
                "id": refund.id,
                "amount": Decimal(refund.amount) / 100,
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
        return {
            "status": "processed",
            "event_type": "payment_intent.succeeded",
            "payment_intent_id": payment_intent["id"]
        }

    async def _handle_payment_failed(
        self,
        payment_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "status": "processed",
            "event_type": "payment_intent.payment_failed",
            "payment_intent_id": payment_intent["id"]
        }

    async def _handle_refund_processed(
        self,
        charge: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "status": "processed",
            "event_type": "charge.refunded",
            "charge_id": charge["id"]
        }

    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> PaymentStatusEnum:
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
        payment.status = new_status
        if external_payment_id:
            payment.external_payment_id = hash(external_payment_id) % (2 ** 31)
        return payment

    async def get_payment_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[PaymentModel]:
        # TODO: implement this
        pass

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        try:
            stripe.Webhook.construct_event(payload, signature, self.secret_key)
            return True
        except (ValueError, Exception):
            return False
