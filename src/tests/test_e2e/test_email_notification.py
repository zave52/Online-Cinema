import base64

import httpx
import pytest
import stripe
from bs4 import BeautifulSoup
from sqlalchemy import select

from database import ActivationTokenModel, UserModel


@pytest.mark.e2e
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_registration(
    e2e_client,
    reset_db_once_for_e2e,
    settings,
    seed_user_groups,
    e2e_db_session
):
    """End-to-end test for user registration."""
    user_data = {"email": "test@gmail.com", "password": "StrongPassword123!"}
    response = await e2e_client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["email"] == user_data["email"]

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    assert mailhog_response.status_code == 200
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0

    email = messages[0]
    assert email["Content"]["Headers"]["To"][0] == user_data["email"]
    email_html = email["MIME"]["Parts"][0]["Body"]
    soup = BeautifulSoup(base64.b64decode(email_html), "html.parser")
    assert soup.find("strong", id="email") is not None


@pytest.mark.e2e
@pytest.mark.order(2)
@pytest.mark.asyncio
async def test_account_activation(e2e_client, settings, e2e_db_session):
    """End-to-end test for account activation."""
    user_email = "test@gmail.com"
    await e2e_client.post(
        "/api/v1/accounts/activate/resend/",
        json={"email": user_email}
    )

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == user_email
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]

    response = await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": user_email, "token": token}
    )
    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.order(3)
@pytest.mark.asyncio
async def test_activation_complete_email(e2e_client, settings, e2e_db_session):
    """End-to-end test for the activation complete email."""
    user_data = {
        "email": "activation.complete@example.com",
        "password": "Password123!"
    }
    await e2e_client.post("/api/v1/accounts/register/", json=user_data)

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == user_data["email"]
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]

    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": user_data["email"], "token": token}
    )

    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No activation complete email sent!"
    assert messages[0]["Content"]["Headers"]["To"][0] == user_data["email"]
    assert messages[0]["Content"]["Headers"]["Subject"][0] == (
        "Account Activation Successfully"
    )


@pytest.mark.e2e
@pytest.mark.order(4)
@pytest.mark.asyncio
async def test_password_reset_complete_email(
    e2e_client,
    settings,
    e2e_db_session
):
    """End-to-end test for the password reset complete email."""
    user_data = {
        "email": "pw.reset.complete@example.com",
        "password": "Password123!"
    }
    await e2e_client.post("/api/v1/accounts/register/", json=user_data)

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == user_data["email"]
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]
    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": user_data["email"], "token": token}
    )

    await e2e_client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": user_data["email"]}
    )

    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    reset_email = [m for m in messages if m["Content"]["Headers"]["Subject"][
        0] == "Password Reset Request"][0]
    email_html = base64.b64decode(reset_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    reset_link = soup.find("a", id="link")["href"]
    token = reset_link.split("token=")[1]

    await e2e_client.post(
        "/api/v1/accounts/password-reset/complete/",
        json={
            "email": user_data["email"],
            "password": "NewPassword123!",
            "token": token
        }
    )

    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No password reset complete email sent!"
    assert messages[0]["Content"]["Headers"]["To"][0] == user_data["email"]
    assert messages[0]["Content"]["Headers"]["Subject"][0] == (
        "Password Reset Complete"
    )


@pytest.mark.e2e
@pytest.mark.order(5)
@pytest.mark.asyncio
async def test_password_changed_email(e2e_client, settings, e2e_db_session):
    """End-to-end test for the password changed email."""
    user_data = {"email": "pw.changed@example.com", "password": "Password123!"}
    await e2e_client.post("/api/v1/accounts/register/", json=user_data)

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == user_data["email"]
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]
    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": user_data["email"], "token": token}
    )

    login_resp = await e2e_client.post(
        "/api/v1/accounts/login/",
        json=user_data
    )
    user_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    await e2e_client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": user_data["password"],
            "new_password": "NewPassword123!"
        },
        headers=headers
    )

    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No password changed email sent!"
    assert messages[0]["Content"]["Headers"]["To"][0] == user_data["email"]
    assert messages[0]["Content"]["Headers"]["Subject"][0] == (
        "Password Change Successfully"
    )


@pytest.mark.e2e
@pytest.mark.order(6)
@pytest.mark.asyncio
async def test_refund_confirmation_email(
    e2e_client,
    settings,
    e2e_db_session,
    seed_movies
):
    """End-to-end test for the refund confirmation email."""
    user_data = {"email": "refund.test@example.com", "password": "Password123!"}
    await e2e_client.post("/api/v1/accounts/register/", json=user_data)
    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == user_data["email"]
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]
    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": user_data["email"], "token": token}
    )
    login_resp = await e2e_client.post(
        "/api/v1/accounts/login/",
        json=user_data
    )
    user_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    movie_id = seed_movies[0]["id"]
    cart_data = {"movie_id": movie_id}
    cart_items_resp = await e2e_client.post(
        f"/api/v1/ecommerce/cart/items/",
        json=cart_data,
        headers=headers
    )
    cart_item_id = cart_items_resp.json()["cart_item_id"]
    order_data = {"cart_item_ids": [cart_item_id]}
    order_resp = await e2e_client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=headers
    )
    order_id = order_resp.json()["id"]
    intent_resp = await e2e_client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json={"order_id": order_id},
        headers=headers
    )
    payment_intent_id = intent_resp.json()["id"]
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.PaymentIntent.confirm(
        payment_intent_id,
        payment_method="pm_card_visa",
        return_url="https://testdomain.com/payment/return"
    )
    await e2e_client.post(
        "/api/v1/ecommerce/payments/process/",
        json={"payment_intent_id": payment_intent_id},
        headers=headers
    )

    refund_data = {"reason": "requested_by_customer"}
    await e2e_client.post(
        f"/api/v1/ecommerce/orders/{order_id}/refund/",
        json=refund_data,
        headers=headers
    )

    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No refund confirmation email sent!"
    assert messages[0]["Content"]["Headers"]["To"][0] == user_data["email"]
    assert messages[0]["Content"]["Headers"]["Subject"][0] == (
        "Refund Confirmation"
    )


@pytest.mark.e2e
@pytest.mark.order(7)
@pytest.mark.asyncio
async def test_comment_reply_notification(
    e2e_client,
    settings,
    e2e_db_session,
    seed_movies
):
    """End-to-end test for comment reply email notification."""
    commenter_data = {
        "email": "commenter.test@example.com",
        "password": "Password123!"
    }
    await e2e_client.post("/api/v1/accounts/register/", json=commenter_data)

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == commenter_data["email"]
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]

    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": commenter_data["email"], "token": token}
    )
    login_resp = await e2e_client.post(
        "/api/v1/accounts/login/",
        json=commenter_data
    )
    commenter_token = login_resp.json()["access_token"]

    replier_data = {
        "email": "replier.test@example.com",
        "password": "Password123!"
    }
    await e2e_client.post("/api/v1/accounts/register/", json=replier_data)

    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == replier_data["email"]
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]

    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": replier_data["email"], "token": token}
    )
    login_resp = await e2e_client.post(
        "/api/v1/accounts/login/",
        json=replier_data
    )
    replier_token = login_resp.json()["access_token"]

    movie_id = seed_movies[0]["id"]
    comment_resp = await e2e_client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json={"content": "Test comment from commenter."},
        headers={"Authorization": f"Bearer {commenter_token}"}
    )
    assert comment_resp.status_code == 201
    comment_id = comment_resp.json()["id"]

    await e2e_client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/{comment_id}/replies/",
        json={"content": "A reply from replier."},
        headers={"Authorization": f"Bearer {replier_token}"}
    )

    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No comment reply email sent!"
    assert messages[0]["Content"]["Headers"]["To"][0] == commenter_data["email"]


@pytest.mark.e2e
@pytest.mark.order(8)
@pytest.mark.asyncio
async def test_payment_confirmation_notification(
    e2e_client,
    settings,
    e2e_db_session,
    seed_movies
):
    """End-to-end test for payment confirmation email notification."""
    user_data = {
        "email": "payment.test@example.com",
        "password": "Password123!"
    }
    await e2e_client.post("/api/v1/accounts/register/", json=user_data)
    stmt = select(ActivationTokenModel).join(UserModel).where(
        UserModel.email == user_data["email"]
    )
    result = await e2e_db_session.execute(stmt)
    token_record = result.scalars().first()
    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": user_data["email"], "token": token_record.token}
    )
    login_resp = await e2e_client.post(
        "/api/v1/accounts/login/",
        json=user_data
    )
    user_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    movie_id = seed_movies[1]["id"]
    add_to_cart_resp = await e2e_client.post(
        f"/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_id},
        headers=headers
    )
    assert add_to_cart_resp.status_code == 200

    cart_item_id = add_to_cart_resp.json()["cart_item_id"]
    order_resp = await e2e_client.post(
        "/api/v1/ecommerce/orders/",
        json={"cart_item_ids": [cart_item_id]},
        headers=headers
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    intent_resp = await e2e_client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json={"order_id": order_id},
        headers=headers
    )
    payment_intent_id = intent_resp.json()["id"]

    stripe.PaymentIntent.confirm(
        payment_intent_id,
        payment_method="pm_card_visa",
        return_url="https://testdomain.com/payment/return"
    )

    process_resp = await e2e_client.post(
        "/api/v1/ecommerce/payments/process/",
        json={"payment_intent_id": payment_intent_id},
        headers=headers
    )
    assert process_resp.status_code == 200

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No payment confirmation email sent!"
    assert messages[0]["Content"]["Headers"]["To"][0] == user_data["email"]
