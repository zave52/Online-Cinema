class BaseSecurityError(Exception):
    """Base exception class for security-related errors.
    
    This is the parent class for all security exceptions in the application.
    It provides a common interface for security error handling.
    """

    def __init__(self, message=None) -> None:
        """Initialize the base security error.
        
        Args:
            message (str, optional): Custom error message. Defaults to generic message.
        """
        if message is None:
            message = "A security error occurred."
        super().__init__(message)


class TokenExpiredError(BaseSecurityError):
    """Exception raised when a JWT token has expired.
    
    This exception is raised when attempting to use a JWT token that has
    passed its expiration time.
    """

    def __init__(self, message="Token has expired.") -> None:
        """Initialize the token expired error.
        
        Args:
            message (str): Error message. Defaults to "Token has expired."
        """
        super().__init__(message)


class InvalidTokenError(BaseSecurityError):
    """Exception raised when a JWT token is invalid or malformed.
    
    This exception is raised when a JWT token cannot be decoded or
    validated due to format issues or invalid signature.
    """

    def __init__(self, message="Invalid token.") -> None:
        """Initialize the invalid token error.
        
        Args:
            message (str): Error message. Defaults to "Invalid token."
        """
        super().__init__(message)
