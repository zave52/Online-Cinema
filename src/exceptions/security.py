class BaseSecurityError(Exception):
    def __init__(self, message=None) -> None:
        if message is None:
            message = "A security error occurred."
        super().__init__(message)


class TokenExpiredError(BaseSecurityError):
    def __int__(self, message="Token has expired.") -> None:
        super().__init__(message)


class InvalidTokenError(BaseSecurityError):
    def __init__(self, message="Invalid token.") -> None:
        super().__init__(message)
