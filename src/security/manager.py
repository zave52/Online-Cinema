from datetime import timedelta, datetime
from typing import Optional

from jose import jwt, ExpiredSignatureError, JWTError

from exceptions.security import TokenExpiredError, InvalidTokenError
from security.interfaces import JWTManagerInterface


class JWTManager(JWTManagerInterface):
    def __init__(
        self,
        access_secret_key: str,
        refresh_secret_key: str,
        access_expires_delta: int,
        refresh_expires_delta: int,
        algorithm: str
    ) -> None:
        self.access_expires_delta: timedelta = timedelta(access_expires_delta)
        self.refresh_expires_delta: timedelta = timedelta(refresh_expires_delta)
        self._access_secret_key = access_secret_key
        self._refresh_secret_key = refresh_secret_key
        self._algorithm = algorithm

    def _create_token(
        self, data: dict, secret_key: str, expires_delta: timedelta
    ) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, key=secret_key, algorithm=self._algorithm)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
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
        return self._create_token(
            data=data,
            secret_key=self._refresh_secret_key,
            expires_delta=expires_delta if expires_delta else self.refresh_expires_delta
        )

    def decode_access_token(self, token: str) -> dict:
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
        self.decode_access_token(token)

    def verify_refresh_token(self, token: str) -> None:
        self.decode_refresh_token(token)
