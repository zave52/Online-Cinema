import re

import email_validator
from email_validator import EmailNotValidError


def validate_password_strength(password: str) -> str:
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
    try:
        email_info = email_validator.validate_email(
            user_email, check_deliverability=False
        )
        email = email_info.normalized
    except EmailNotValidError as e:
        raise ValueError(str(e))
    else:
        return email
