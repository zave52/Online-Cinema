from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional


class JWTManagerInterface(ABC):
    """Abstract interface for JWT token management.

    This interface defines the contract for JWT token operations including
    creation, decoding, and verification of access and refresh tokens.
    """

    @abstractmethod
    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create an access token for user authentication.

        Args:
            data (dict): Data to encode in the access token.
            expires_delta (Optional[timedelta]): Custom expiration time.

        Returns:
            str: Encoded access token.
        """
        pass

    @abstractmethod
    def create_refresh_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a refresh token for obtaining new access tokens.

        Args:
            data (dict): Data to encode in the refresh token.
            expires_delta (Optional[timedelta]): Custom expiration time.

        Returns:
            str: Encoded refresh token.
        """
        pass

    @abstractmethod
    def decode_access_token(self, token: str) -> dict:
        """Decode and validate an access token.

        Args:
            token (str): The access token to decode.

        Returns:
            dict: Decoded token data.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or malformed.
        """
        pass

    @abstractmethod
    def decode_refresh_token(self, token: str) -> dict:
        """Decode and validate a refresh token.

        Args:
            token (str): The refresh token to decode.

        Returns:
            dict: Decoded token data.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or malformed.
        """
        pass

    @abstractmethod
    def verify_access_token(self, token: str) -> None:
        """Verify that an access token is valid without returning its data.

        Args:
            token (str): The access token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or malformed.
        """
        pass

    @abstractmethod
    def verify_refresh_token(self, token: str) -> None:
        """Verify that a refresh token is valid without returning its data.

        Args:
            token (str): The refresh token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or malformed.
        """
        pass
