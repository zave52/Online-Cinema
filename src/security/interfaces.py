from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional


class JWTManagerInterface(ABC):
    @abstractmethod
    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        pass

    @abstractmethod
    def create_refresh_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        pass

    @abstractmethod
    def decode_access_token(self, token: str) -> dict:
        pass

    @abstractmethod
    def decode_refresh_token(self, token: str) -> dict:
        pass

    @abstractmethod
    def verify_access_token(self, token: str) -> None:
        pass

    @abstractmethod
    def verify_refresh_token(self, token: str) -> None:
        pass
