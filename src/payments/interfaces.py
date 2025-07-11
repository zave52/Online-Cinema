from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatusEnum
from notifications.interfaces import EmailSenderInterface


class PaymentServiceInterface(ABC):
    """Abstract interface for payment processing services.
    
    This interface defines the contract for payment operations including
    payment intent creation, processing, refunds, webhook handling, and
    payment status management.
    """

    @abstractmethod
    async def create_payment_intent(
        self,
        order: OrderModel,
        amount: Decimal,
        currency: str = "usd"
    ) -> Dict[str, Any]:
        """Create a payment intent for processing payments.
        
        Args:
            order (OrderModel): The order to create payment intent for.
            amount (Decimal): Payment amount.
            currency (str): Payment currency code.
            
        Returns:
            Dict[str, Any]: Payment intent data from payment provider.
        """
        pass

    @abstractmethod
    async def process_payment(
        self,
        payment_intent_id: str,
        order: OrderModel,
        user_id: int
    ) -> PaymentModel:
        """Process a payment using the payment intent.
        
        Args:
            payment_intent_id (str): ID of the payment intent.
            order (OrderModel): The order being paid for.
            user_id (int): ID of the user making the payment.
            
        Returns:
            PaymentModel: Created payment record.
        """
        pass

    @abstractmethod
    async def confirm_payment(self, payment_intent_id: str) -> bool:
        """Confirm a payment intent.
        
        Args:
            payment_intent_id (str): ID of the payment intent to confirm.
            
        Returns:
            bool: True if payment was confirmed successfully.
        """
        pass

    @abstractmethod
    async def cancel_payment(self, payment_intent_id: str) -> bool:
        """Cancel a payment intent.
        
        Args:
            payment_intent_id (str): ID of the payment intent to cancel.
            
        Returns:
            bool: True if payment was cancelled successfully.
        """
        pass

    @abstractmethod
    async def process_refund(
        self,
        payment: PaymentModel,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a refund for a payment.
        
        Args:
            payment (PaymentModel): The payment to refund.
            amount (Optional[Decimal]): Amount to refund (full amount if None).
            reason (Optional[str]): Reason for the refund.
            
        Returns:
            Dict[str, Any]: Refund data from payment provider.
        """
        pass

    @abstractmethod
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
        db: AsyncSession,
        email_sender: EmailSenderInterface
    ) -> Dict[str, Any]:
        """Handle webhook events from payment provider.
        
        Args:
            payload (bytes): Raw webhook payload.
            signature (str): Webhook signature for verification.
            db (AsyncSession): Database session dependency.
            email_sender (EmailSenderInterface): Email sender dependency.
            
        Returns:
            Dict[str, Any]: Processed webhook event data.
        """
        pass

    @abstractmethod
    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> PaymentStatusEnum:
        """Get the current status of a payment.
        
        Args:
            payment_intent_id (str): ID of the payment intent.
            
        Returns:
            PaymentStatusEnum: Current payment status.
        """
        pass

    @abstractmethod
    async def validate_payment_method(self, payment_method_id: str) -> bool:
        """Validate a payment method.
        
        Args:
            payment_method_id (str): ID of the payment method to validate.
            
        Returns:
            bool: True if payment method is valid.
        """
        pass

    @abstractmethod
    async def create_checkout_session(
        self,
        order: OrderModel,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a checkout session for payment.
        
        Args:
            order (OrderModel): The order for checkout session.
            success_url (str): URL to redirect on successful payment.
            cancel_url (str): URL to redirect on cancelled payment.
            
        Returns:
            Dict[str, Any]: Checkout session data.
        """
        pass

    @abstractmethod
    async def retrieve_payment_intent(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """Retrieve payment intent details from payment provider.
        
        Args:
            payment_intent_id (str): ID of the payment intent.
            
        Returns:
            Dict[str, Any]: Payment intent details.
        """
        pass

    @abstractmethod
    async def update_payment_status(
        self,
        payment: PaymentModel,
        new_status: PaymentStatusEnum,
        external_payment_id: Optional[str] = None
    ) -> PaymentModel:
        """Update the status of a payment.
        
        Args:
            payment (PaymentModel): The payment to update.
            new_status (PaymentStatusEnum): New payment status.
            external_payment_id (Optional[str]): External payment ID from provider.
            
        Returns:
            PaymentModel: Updated payment record.
        """
        pass

    @abstractmethod
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify webhook signature for security.
        
        Args:
            payload (bytes): Raw webhook payload.
            signature (str): Webhook signature to verify.
            
        Returns:
            bool: True if signature is valid.
        """
        pass
