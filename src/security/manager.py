from datetime import timedelta, datetime, timezone
from typing import Optional

from jose import jwt, ExpiredSignatureError, JWTError

from exceptions.security import TokenExpiredError, InvalidTokenError
from security.interfaces import JWTManagerInterface


class JWTManager(JWTManagerInterface):
    """JWT token manager for handling access and refresh tokens.

    This class provides functionality for creating, decoding, and verifying
    JWT tokens for user authentication and session management.
    """

    def __init__(
        self,
        access_secret_key: str,
        refresh_secret_key: str,
        access_expires_delta: int,
        refresh_expires_delta: int,
        algorithm: str
    ) -> None:
        """Initialize the JWT manager with configuration.

        Args:
            access_secret_key (str): Secret key for signing access tokens.
            refresh_secret_key (str): Secret key for signing refresh tokens.
            access_expires_delta (int): Access token expiration time in minutes.
            refresh_expires_delta (int): Refresh token expiration time in minutes.
            algorithm (str): JWT signing algorithm (e.g., 'HS256').
        """
        self.access_expires_delta: timedelta = timedelta(
            minutes=access_expires_delta
        )
        self.refresh_expires_delta: timedelta = timedelta(
            minutes=refresh_expires_delta
        )
        self._access_secret_key = access_secret_key
        self._refresh_secret_key = refresh_secret_key
        self._algorithm = algorithm

    def _create_token(
        self, data: dict, secret_key: str, expires_delta: timedelta
    ) -> str:
        """Create a JWT token with the given data and expiration.

        Args:
            data (dict): Data to encode in the token.
            secret_key (str): Secret key for signing the token.
            expires_delta (timedelta): Token expiration time.

        Returns:
            str: Encoded JWT token.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, key=secret_key, algorithm=self._algorithm)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create an access token for user authentication.

        Args:
            data (dict): Data to encode in the access token.
            expires_delta (Optional[timedelta]): Custom expiration time.

        Returns:
            str: Encoded access token.
        """
        return self._create_token(
            data=data,
            secret_key=self._access_secret_key,
            expires_delta=expires_delta if expires_delta else self.access_expires_delta
        )

    def create_refresh_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a refresh token for obtaining new access tokens.

        Args:
            data (dict): Data to encode in the refresh token.
            expires_delta (Optional[timedelta]): Custom expiration time.

        Returns:
            str: Encoded refresh token.
        """
        return self._create_token(
            data=data,
            secret_key=self._refresh_secret_key,
            expires_delta=expires_delta if expires_delta else self.refresh_expires_delta
        )

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
        try:
            return jwt.decode(
                token,
                self._access_secret_key,
                algorithms=[self._algorithm]
            )
        except ExpiredSignatureError:
            raise TokenExpiredError
        except JWTError:
            raise InvalidTokenError

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
        try:
            return jwt.decode(
                token,
                self._refresh_secret_key,
                algorithms=[self._algorithm]
            )
        except ExpiredSignatureError:
            raise TokenExpiredError
        except JWTError:
            raise InvalidTokenError

    def verify_access_token(self, token: str) -> None:
        """Verify that an access token is valid without returning its data.

        Args:
            token (str): The access token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or malformed.
        """
        self.decode_access_token(token)

    def verify_refresh_token(self, token: str) -> None:
        """Verify that a refresh token is valid without returning its data.

        Args:
            token (str): The refresh token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or malformed.
        """
        self.decode_refresh_token(token)
