import io
import os
import uuid
from decimal import Decimal
from typing import AsyncGenerator, Any

import pytest
import pytest_asyncio
from PIL import Image
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker, AsyncEngine
)
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool

from config.dependencies import (
    get_email_sender,
    get_s3_storage,
    get_payment_service
)
from config.settings import get_settings
from database import get_db
from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum
from database.models.base import Base
from database.models.movies import MovieModel, CertificationModel
from database.models.orders import OrderModel, OrderStatusEnum, OrderItemModel
from main import create_app
from security.manager import JWTManager
from tests.doubles.fakes.payments import FakePaymentService
from tests.doubles.fakes.storage import FakeStorage
from tests.doubles.stubs.emails import StubEmailSender


@pytest_asyncio.fixture(scope="session")
def app() -> FastAPI:
    os.environ["ENVIRONMENT"] = "testing"
    app = create_app()
    return app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def async_engine() -> AsyncGenerator[AsyncEngine, Any]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, Any]:
    """Provide an async database session for database interactions."""
    async_session_local = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session_local() as session:
        existing_groups = await session.execute(select(UserGroupModel))
        existing_groups_list = existing_groups.scalars().all()

        if not existing_groups_list:
            groups = [
                UserGroupModel(name=UserGroupEnum.USER),
                UserGroupModel(name=UserGroupEnum.MODERATOR),
                UserGroupModel(name=UserGroupEnum.ADMIN)
            ]
            session.add_all(groups)
            await session.commit()

        existing_certs = await session.execute(select(CertificationModel))
        existing_certs_list = existing_certs.scalars().all()

        if not existing_certs_list:
            certifications = [
                CertificationModel(name="G"),
                CertificationModel(name="PG"),
                CertificationModel(name="R")
            ]
            session.add_all(certifications)
            await session.commit()

        yield session


@pytest_asyncio.fixture(scope="function")
async def email_sender_stub():
    """Provide a stub implementation of the email sender."""
    return StubEmailSender()


@pytest_asyncio.fixture(scope="function")
async def s3_storage_fake():
    """Provide a fake S3 storage client."""
    return FakeStorage()


@pytest_asyncio.fixture(scope="function")
async def payment_service_fake():
    """Provide a fake payment service for testing."""
    return FakePaymentService()


@pytest_asyncio.fixture(scope="function")
async def client(
    app,
    email_sender_stub,
    s3_storage_fake,
    payment_service_fake,
    db_session
) -> AsyncGenerator[AsyncClient, Any]:
    """Provide an asynchronous HTTP client for testing."""
    app.dependency_overrides[get_email_sender] = lambda: email_sender_stub
    app.dependency_overrides[get_s3_storage] = lambda: s3_storage_fake
    app.dependency_overrides[get_payment_service] = lambda: payment_service_fake

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest.fixture
def user_data() -> dict:
    return {
        "email": "testuser@gmail.com",
        "password": "StrongPass123!"
    }


@pytest_asyncio.fixture(scope="function")
async def activated_user(
    client,
    user_data,
    admin_token
) -> dict[str, dict[str, str]]:
    """Create a user, activate them, and return user data with access token."""

    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"activated_{uuid.uuid4().hex[:8]}@example.com"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    activation_resp = await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )
    assert activation_resp.status_code == 200

    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    return {
        "user_id": user_id,
        "email": unique_user_data["email"],
        "password": unique_user_data["password"],
        "access_token": login_data["access_token"],
        "refresh_token": login_data["refresh_token"],
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"}
    }


@pytest_asyncio.fixture(scope="function")
async def seed_movies(db_session) -> list[dict[str, Any]]:
    result = await db_session.execute(select(MovieModel))
    existing_movies = result.scalars().all()

    if existing_movies:
        return [{
            "id": m.id,
            "name": m.name,
            "year": m.year,
            "imdb": m.imdb,
            "description": m.description,
            "price": float(m.price)
        } for m in existing_movies[:2]]

    cert_result = await db_session.execute(
        select(CertificationModel).where(CertificationModel.id == 1)
    )
    existing_cert = cert_result.scalars().first()

    if not existing_cert:
        certification = CertificationModel(id=1, name="PG")
        db_session.add(certification)
        await db_session.commit()
        await db_session.refresh(certification)

    unique_suffix = str(uuid.uuid4())[:8]

    movies = [
        MovieModel(
            name=f"Movie1-{unique_suffix}",
            year=2020,
            time=120,
            imdb=7.0,
            votes=100,
            meta_score=75.0,
            gross=50000000.0,
            description="Desc1",
            price=10.0,
            certification_id=1,

        ),
        MovieModel(
            name=f"Movie2-{unique_suffix}",
            year=2021,
            time=90,
            imdb=8.0,
            votes=200,
            meta_score=85.0,
            gross=75000000.0,
            description="Desc2",
            price=12.0,
            certification_id=1
        ),
    ]
    db_session.add_all(movies)
    await db_session.commit()
    for m in movies:
        await db_session.refresh(m)
    return [{
        "id": m.id,
        "name": m.name,
        "year": m.year,
        "imdb": m.imdb,
        "description": m.description,
        "price": float(m.price),
        "time": m.time,
        "votes": m.votes,
        "meta_score": m.meta_score,
        "gross": m.gross,
    } for m in movies]


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session) -> dict[str, Any]:
    """Create an admin user in the database and return admin data."""
    admin_email = "admin@gmail.com"
    stmt = select(UserModel).where(UserModel.email == admin_email)
    result = await db_session.execute(stmt)
    existing_admin = result.scalars().first()

    if existing_admin:
        return {
            "user_id": existing_admin.id,
            "email": existing_admin.email,
            "group_id": existing_admin.group_id
        }

    stmt = select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.ADMIN
    )
    result = await db_session.execute(stmt)
    admin_group = result.scalars().first()

    if not admin_group:
        raise Exception("Admin group not found in database")

    admin_user = UserModel.create(
        email=admin_email,
        raw_password="AdminPass123!",
        group_id=admin_group.id
    )
    admin_user.is_active = True

    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user)

    return {
        "user_id": admin_user.id,
        "email": admin_user.email,
        "group_id": admin_user.group_id
    }


@pytest.fixture
def admin_token(admin_user) -> str:
    """Create admin JWT token using real admin user data."""
    settings = get_settings()
    payload = {
        "sub": admin_user["email"],
        "role": "admin",
        "user_id": admin_user["user_id"],
    }
    token = jwt.encode(
        payload,
        settings.SECRET_KEY_ACCESS,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )
    return token


@pytest_asyncio.fixture(scope="function")
async def pending_order(db_session, activated_user, seed_movies) -> OrderModel:
    """Create a pending order with order items for testing payments."""
    if not seed_movies:
        cert_result = await db_session.execute(
            select(CertificationModel).where(CertificationModel.id == 1)
        )
        existing_cert = cert_result.scalars().first()

        if not existing_cert:
            certification = CertificationModel(id=1, name="PG")
            db_session.add(certification)
            await db_session.commit()
            await db_session.refresh(certification)

        test_movie = MovieModel(
            name="Test Movie for Payment",
            year=2023,
            time=120,
            imdb=7.5,
            votes=1000,
            meta_score=80.0,
            gross=10000000.0,
            description="Test movie for payment testing",
            price=Decimal("29.97"),
            certification_id=1
        )
        db_session.add(test_movie)
        await db_session.commit()
        await db_session.refresh(test_movie)
        movie_data = {
            "id": test_movie.id,
            "name": test_movie.name,
            "price": float(test_movie.price)
        }
    else:
        movie_data = seed_movies[0]
        movie_result = await db_session.execute(
            select(MovieModel).where(MovieModel.id == movie_data["id"])
        )
        test_movie = movie_result.scalars().first()

    order = OrderModel(
        user_id=activated_user["user_id"],
        status=OrderStatusEnum.PENDING,
        total_amount=Decimal(str(movie_data["price"]))
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    order_item = OrderItemModel(
        order_id=order.id,
        movie_id=test_movie.id,
        price_at_order=Decimal(str(movie_data["price"]))
    )
    db_session.add(order_item)
    await db_session.commit()
    await db_session.refresh(order_item)

    order_with_items_result = await db_session.execute(
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
        .where(OrderModel.id == order.id)
    )
    order_with_items = order_with_items_result.scalars().first()

    return order_with_items


def create_test_image() -> bytes:
    """Create a minimal valid JPEG image for testing."""
    img = Image.new('RGB', (1, 1), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


@pytest.fixture
def jwt_manager():
    return JWTManager(
        access_secret_key="access_secret",
        refresh_secret_key="refresh_secret",
        access_expires_delta=1,
        refresh_expires_delta=2,
        algorithm="HS256"
    )


@pytest.fixture
def email_sender():
    sender = StubEmailSender()
    sender.clear_sent_emails()
    return sender
