import re

import pytest

from security.utils import (
    hash_password,
    verify_password,
    generate_secure_token
)


@pytest.mark.unit
def test_hash_password_and_verify_password():
    raw_password = "SuperSecret123!"
    hashed = hash_password(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed)
    assert not verify_password("WrongPassword", hashed)


@pytest.mark.unit
def test_generate_secure_token_length_and_format():
    length = 32
    token = generate_secure_token(length)
    assert isinstance(token, str)
    assert len(token) >= length
    assert re.match(r'^[A-Za-z0-9\-_]+$', token)
