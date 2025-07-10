from typing import cast

import pytest
from pydantic import EmailStr


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_activation_email_stub(email_sender):
    await email_sender.send_activation_email(
        email=cast(EmailStr, "user@example.com"),
        activation_link="https://example.com/activate/abc"
    )
    sent = email_sender.get_sent_emails()
    assert len(sent) == 1
    email_data = sent[0]
    assert email_data["type"] == "activation"
    assert email_data["recipient"] == "user@example.com"
    assert email_data["activation_link"] == "https://example.com/activate/abc"
    assert email_data["subject"] == "Account Activation"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_activation_complete_email_stub(email_sender):
    await email_sender.send_activation_complete_email(
        email=cast(EmailStr, "user2@example.com"),
        login_link="https://example.com/login"
    )
    sent = email_sender.get_sent_emails()
    assert len(sent) == 1
    email_data = sent[0]
    assert email_data["type"] == "activation_complete"
    assert email_data["recipient"] == "user2@example.com"
    assert email_data["login_link"] == "https://example.com/login"
    assert email_data["subject"] == "Account Activation Successfully"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_password_reset_email_stub(email_sender):
    await email_sender.send_password_reset_email(
        email=cast(EmailStr, "user3@example.com"),
        password_reset_link="https://example.com/reset/xyz"
    )
    sent = email_sender.get_sent_emails()
    assert len(sent) == 1
    email_data = sent[0]
    assert email_data["type"] == "password_reset"
    assert email_data["recipient"] == "user3@example.com"
    assert email_data["reset_link"] == "https://example.com/reset/xyz"
    assert email_data["subject"] == "Password Reset Request"
