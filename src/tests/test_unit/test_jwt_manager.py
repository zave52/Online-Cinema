import time
from datetime import timedelta

import pytest

from exceptions.security import TokenExpiredError, InvalidTokenError


@pytest.mark.unit
def test_create_and_decode_access_token(jwt_manager):
    data = {"sub": "user1", "role": "admin"}
    token = jwt_manager.create_access_token(data)
    decoded = jwt_manager.decode_access_token(token)
    assert decoded["sub"] == "user1"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


@pytest.mark.unit
def test_create_and_decode_refresh_token(jwt_manager):
    data = {"sub": "user2"}
    token = jwt_manager.create_refresh_token(data)
    decoded = jwt_manager.decode_refresh_token(token)
    assert decoded["sub"] == "user2"
    assert "exp" in decoded


@pytest.mark.unit
def test_access_token_expiry(jwt_manager):
    data = {"sub": "user3"}
    token = jwt_manager.create_access_token(
        data,
        expires_delta=timedelta(seconds=1)
    )
    time.sleep(2)
    with pytest.raises(TokenExpiredError):
        jwt_manager.decode_access_token(token)


@pytest.mark.unit
def test_refresh_token_expiry(jwt_manager):
    data = {"sub": "user4"}
    token = jwt_manager.create_refresh_token(
        data,
        expires_delta=timedelta(seconds=1)
    )
    time.sleep(2)
    with pytest.raises(TokenExpiredError):
        jwt_manager.decode_refresh_token(token)


@pytest.mark.unit
def test_invalid_access_token(jwt_manager):
    with pytest.raises(InvalidTokenError):
        jwt_manager.decode_access_token("invalid.token.value")


@pytest.mark.unit
def test_invalid_refresh_token(jwt_manager):
    with pytest.raises(InvalidTokenError):
        jwt_manager.decode_refresh_token("invalid.token.value")


@pytest.mark.unit
def test_verify_access_token(jwt_manager):
    data = {"sub": "user5"}
    token = jwt_manager.create_access_token(data)
    jwt_manager.verify_access_token(token)


@pytest.mark.unit
def test_verify_refresh_token(jwt_manager):
    data = {"sub": "user6"}
    token = jwt_manager.create_refresh_token(data)
    jwt_manager.verify_refresh_token(token)
