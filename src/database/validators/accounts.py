import re

import email_validator
from email_validator import EmailNotValidError


def validate_password_strength(password: str) -> str:
    """Validate password strength requirements.
    
    Checks that the password meets minimum security requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Args:
        password (str): The password to validate.
        
    Returns:
        str: The validated password.
        
    Raises:
        ValueError: If the password doesn't meet strength requirements.
    """
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[@$!%*?&#]).*$"
    if not re.match(pattern, password):
        raise ValueError(
            "Password must contain at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character (@, $, !, %, *, ?, &, #)."
        )

    return password


def validate_email(user_email: str) -> str:
    """Validate and normalize email address.
    
    Uses email-validator library to validate email format and normalize it.
    
    Args:
        user_email (str): The email address to validate.
        
    Returns:
        str: The normalized email address.
        
    Raises:
        ValueError: If the email address is invalid.
    """
    try:
        email_info = email_validator.validate_email(
            user_email, check_deliverability=False
        )
        email = email_info.normalized
    except EmailNotValidError as e:
        raise ValueError(str(e))
    else:
        return email
