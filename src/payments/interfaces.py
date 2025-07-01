from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatusEnum


class PaymentServiceInterface(ABC):
    @abstractmethod
    async def create_payment_intent(
        self,
        order: OrderModel,
        amount: float,
        currency: str = "usd"
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def process_payment(
        self,
        payment_intent_id: str,
        order: OrderModel,
        user_id: int
    ) -> PaymentModel:
        pass

    @abstractmethod
    async def confirm_payment(self, payment_intent_id: str) -> bool:
        pass

    @abstractmethod
    async def cancel_payment(self, payment_intent_id: str) -> bool:
        pass

    @abstractmethod
    async def process_refund(
        self,
        payment: PaymentModel,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> PaymentStatusEnum:
        pass

    @abstractmethod
    async def validate_payment_method(self, payment_method_id: str) -> bool:
        pass

    @abstractmethod
    async def create_checkout_session(
        self,
        order: OrderModel,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def retrieve_payment_intent(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def update_payment_status(
        self,
        payment: PaymentModel,
        new_status: PaymentStatusEnum,
        external_payment_id: Optional[str] = None
    ) -> PaymentModel:
        pass

    @abstractmethod
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        pass
