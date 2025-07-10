import pytest
import uuid


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_email_notification_registration_flow(
    client,
    user_data,
    email_sender_stub
):
    """Test email notification flow during registration."""
    email_sender_stub.clear_sent_emails()

    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"email_test_{uuid.uuid4().hex[:8]}@example.com"
    unique_user_data["username"] = f"email_test_{uuid.uuid4().hex[:8]}"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert reg_resp.status_code == 201

    sent_emails = email_sender_stub.get_sent_emails()
    assert len(sent_emails) == 1

    activation_email = sent_emails[0]
    assert activation_email["type"] == "activation"
    assert activation_email["recipient"] == unique_user_data["email"]
    assert activation_email["subject"] == "Account Activation"
    assert "activation_link" in activation_email

    user_emails = email_sender_stub.get_sent_emails_by_recipient(
        unique_user_data["email"]
    )
    assert len(user_emails) == 1

    email_sender_stub.clear_sent_emails()

    resend_resp = await client.post(
        "/api/v1/accounts/activate/resend/",
        json={"email": unique_user_data["email"]}
    )
    assert resend_resp.status_code == 200

    resend_emails = email_sender_stub.get_sent_emails()
    assert len(resend_emails) == 1

    resend_email = resend_emails[0]
    assert resend_email["type"] == "activation"
    assert resend_email["recipient"] == unique_user_data["email"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_email_notification_password_reset_flow(
    client,
    user_data,
    email_sender_stub
):
    """Test email notification flow during password reset."""
    email_sender_stub.clear_sent_emails()

    await client.post("/api/v1/accounts/register/", json=user_data)

    email_sender_stub.clear_sent_emails()

    reset_resp = await client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": user_data["email"]}
    )
    assert reset_resp.status_code == 200

    sent_emails = email_sender_stub.get_sent_emails()
    assert len(sent_emails) == 1

    reset_email = sent_emails[0]
    assert reset_email["type"] == "password_reset"
    assert reset_email["recipient"] == user_data["email"]
    assert reset_email["subject"] == "Password Reset Request"
    assert "reset_link" in reset_email

    email_sender_stub.clear_sent_emails()

    fake_reset_resp = await client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": "nonexistent@example.com"}
    )
    assert fake_reset_resp.status_code == 200

    fake_emails = email_sender_stub.get_sent_emails()
    assert len(fake_emails) == 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_email_notification_password_change_flow(
    client,
    user_data,
    email_sender_stub,
    activated_user
):
    """Test email notification flow during password change."""
    email_sender_stub.clear_sent_emails()

    user_email = activated_user["email"]
    token = activated_user["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    change_resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": user_data["password"],
            "new_password": "NewPassword123!"
        },
        headers=headers
    )

    assert change_resp.status_code == 200

    sent_emails = email_sender_stub.get_sent_emails()
    assert len(sent_emails) == 1

    change_email = sent_emails[0]
    assert change_email["type"] == "password_changed"
    assert change_email["recipient"] == user_email
    assert change_email["subject"] == "Password Change Successfully"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_email_notification_activation_complete_flow(
    client,
    user_data,
    email_sender_stub
):
    """Test email notification when user activation is completed."""
    email_sender_stub.clear_sent_emails()

    unique_user_data = user_data.copy()
    unique_user_data[
        "email"] = f"activation_test_{uuid.uuid4().hex[:8]}@example.com"
    unique_user_data["username"] = f"activation_test_{uuid.uuid4().hex[:8]}"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert reg_resp.status_code == 201

    sent_emails = email_sender_stub.get_sent_emails()
    assert len(sent_emails) == 1
    activation_email = sent_emails[0]
    assert activation_email["type"] == "activation"

    email_sender_stub.clear_sent_emails()

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_email_notification_types_are_distinct(
    client,
    user_data,
    admin_token,
    email_sender_stub
):
    """Test that different email notification types are properly categorized."""
    email_sender_stub.clear_sent_emails()

    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"types_test_{uuid.uuid4().hex[:8]}@example.com"
    unique_user_data["username"] = f"types_test_{uuid.uuid4().hex[:8]}"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)

    admin_headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    await client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": unique_user_data["email"]}
    )

    sent_emails = email_sender_stub.get_sent_emails()
    assert len(sent_emails) == 3

    activation_emails = email_sender_stub.get_sent_emails_by_type("activation")
    reset_emails = email_sender_stub.get_sent_emails_by_type("password_reset")

    assert len(activation_emails) == 1
    assert len(reset_emails) == 1

    assert activation_emails[0]["subject"] == "Account Activation"
    assert "activation_link" in activation_emails[0]

    assert reset_emails[0]["subject"] == "Password Reset Request"
    assert "reset_link" in reset_emails[0]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_email_sender_stub_functionality(email_sender_stub):
    """Test the email sender stub functionality directly."""
    assert len(email_sender_stub.get_sent_emails()) == 0
    assert email_sender_stub.call_count == 0

    await email_sender_stub.send_activation_email(
        "test@example.com",
        "http://activation-link"
    )
    await email_sender_stub.send_password_reset_email(
        "test@example.com",
        "http://reset-link"
    )

    assert len(email_sender_stub.get_sent_emails()) == 2
    assert email_sender_stub.call_count == 2

    user_emails = email_sender_stub.get_sent_emails_by_recipient(
        "test@example.com"
    )
    assert len(user_emails) == 2

    activation_emails = email_sender_stub.get_sent_emails_by_type("activation")
    reset_emails = email_sender_stub.get_sent_emails_by_type("password_reset")

    assert len(activation_emails) == 1
    assert len(reset_emails) == 1

    email_sender_stub.clear_sent_emails()
    assert len(email_sender_stub.get_sent_emails()) == 0
    assert email_sender_stub.call_count == 0
