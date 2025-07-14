import secrets

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw_password: str) -> str:
    """Hash a plain text password using bcrypt.

    Args:
        raw_password (str): The plain text password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(raw_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.

    Args:
        length (int): The length of the token in bytes (default: 32).

    Returns:
        str: A URL-safe base64-encoded random token.
    """
    return secrets.token_urlsafe(length)
