import io
import os
from datetime import date
from decimal import Decimal
from typing import AsyncGenerator, Any, cast
from unittest.mock import MagicMock

import pytest_asyncio
from PIL import Image
from fastapi import FastAPI, UploadFile
from httpx import AsyncClient, ASGITransport
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import (
    get_email_sender,
    get_s3_storage,
    get_payment_service
)
from config.settings import get_settings, BaseAppSettings
from database import (
    get_db_contextmanager,
    reset_database,
    UserProfileModel,
    GenderEnum
)
from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum
from database.models.movies import MovieModel, CertificationModel
from database.models.orders import OrderModel, OrderStatusEnum, OrderItemModel
from main import create_app
from security.interfaces import JWTManagerInterface
from security.manager import JWTManager
from storages.interfaces import S3StorageInterface
from storages.s3 import S3Storage
from tests.doubles.fakes.payments import FakePaymentService
from tests.doubles.fakes.storage import FakeStorage
from tests.doubles.stubs.emails import StubEmailSender


@pytest_asyncio.fixture(scope="session")
def app() -> FastAPI:
    """
    Session-scoped fixture to create and return a FastAPI app instance for testing.
    Sets the environment variable to 'testing' before app creation.
    """
    os.environ["ENVIRONMENT"] = "testing"
    app = create_app()
    return app


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, Any]:
    """
    Function-scoped fixture to provide a database session for each test function.
    Yields an asynchronous SQLAlchemy session.
    """
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def e2e_db_session() -> AsyncGenerator[AsyncSession, Any]:
    """
    Session-scoped fixture to provide a database session for end-to-end tests.
    Yields an asynchronous SQLAlchemy session.
    """
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_db(request):
    """
    Fixture to reset the database to a clean state before each test function.
    Skips the reset for end-to-end tests.
    """
    if "e2e" in request.keywords:
        yield
    else:
        await reset_database()
        yield


@pytest_asyncio.fixture(scope="session")
async def reset_db_once_for_e2e(request):
    """
    Fixture to reset the database once for end-to-end tests.
    """
    await reset_database()


@pytest_asyncio.fixture(scope="session")
async def settings() -> BaseAppSettings:
    """
    Session-scoped fixture to provide application settings.
    Returns an instance of BaseAppSettings.
    """
    return get_settings()


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


@pytest_asyncio.fixture(scope="session")
async def s3_client(settings: BaseAppSettings) -> S3StorageInterface:
    """
    Session-scoped fixture to provide a configured S3 storage client.
    Uses settings from BaseAppSettings.
    """
    return S3Storage(
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        bucket_name=settings.S3_BUCKET_NAME
    )


@pytest_asyncio.fixture(scope="function")
async def jwt_manager(settings: BaseAppSettings) -> JWTManagerInterface:
    """
    Function-scoped fixture to provide a JWT manager for creating and verifying tokens.
    Uses settings from BaseAppSettings.
    """
    return JWTManager(
        access_secret_key=settings.SECRET_KEY_ACCESS,
        refresh_secret_key=settings.SECRET_KEY_REFRESH,
        access_expires_delta=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_expires_delta=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


@pytest_asyncio.fixture(scope="function")
async def client(
    app,
    email_sender_stub,
    s3_storage_fake,
    payment_service_fake,
) -> AsyncGenerator[AsyncClient, Any]:
    """
    Provide an asynchronous HTTP client for testing.
    Overrides app dependencies with test doubles.
    """
    app.dependency_overrides[get_email_sender] = lambda: email_sender_stub
    app.dependency_overrides[get_s3_storage] = lambda: s3_storage_fake
    app.dependency_overrides[get_payment_service] = lambda: payment_service_fake

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def e2e_client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    """
    Session-scoped fixture to provide an asynchronous HTTP client for end-to-end testing.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as async_client:
        yield async_client


@pytest_asyncio.fixture(scope="function")
async def seed_user_groups(
    db_session: AsyncSession
) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture to seed user groups into the database for testing.
    Inserts all UserGroupEnum values as groups.
    """
    groups = [
        UserGroupModel(name=UserGroupEnum.USER),
        UserGroupModel(name=UserGroupEnum.MODERATOR),
        UserGroupModel(name=UserGroupEnum.ADMIN)
    ]
    db_session.add_all(groups)
    await db_session.commit()
    yield db_session


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session, seed_user_groups) -> dict[str, Any]:
    """
    Create an admin user in the database and return admin data.
    If the admin user already exists, retrieve and return their data.
    """
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
        email=cast(EmailStr, admin_email),
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


@pytest_asyncio.fixture(scope="function")
async def admin_headers(admin_user, jwt_manager) -> dict[str, str]:
    """Create admin JWT token using real admin user data."""
    admin_access_token = jwt_manager.create_access_token(
        {"user_id": admin_user["user_id"]}
    )
    return {"Authorization": f"Bearer {admin_access_token}"}


@pytest_asyncio.fixture(scope="function")
async def activated_user(
    db_session,
    settings,
    seed_user_groups,
    jwt_manager
) -> dict[str, Any]:
    """
    Create a user, activate them, and return user data with access token.
    If the user already exists, retrieve and return their data.
    """
    user_data = {
        "email": "activateduser@gmail.com",
        "password": "StrongPass123!"
    }

    stmt = select(UserModel).where(UserModel.email == user_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()

    if not user:
        stmt = select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.USER
        )
        result = await db_session.execute(stmt)
        user_group = result.scalars().first()

        user = UserModel.create(
            email=cast(EmailStr, user_data["email"]),
            raw_password=user_data["password"],
            group_id=user_group.id
        )
        user.is_active = True

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})

    headers = {"Authorization": f"Bearer {jwt_access_token}"}

    return {
        "user_id": user.id,
        "email": user.email,
        "password": user_data["password"],
        "access_token": jwt_access_token,
        "headers": headers
    }


@pytest_asyncio.fixture(scope="function")
async def user_with_profile(
    db_session,
    activated_user,
    mock_avatar
) -> dict[str, Any]:
    """Create a user with a profile for testing."""
    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": GenderEnum.MAN,
        "date_of_birth": date(1990, 1, 1),
        "info": "Test user"
    }

    profile = UserProfileModel(
        user_id=activated_user["user_id"],
        first_name=profile_data["first_name"],
        last_name=profile_data["last_name"],
        gender=profile_data["gender"],
        avatar=mock_avatar.file.read(),
        date_of_birth=profile_data["date_of_birth"],
        info=profile_data["info"]
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    return activated_user


@pytest_asyncio.fixture(scope="function")
async def another_user(db_session, settings, jwt_manager) -> dict[str, Any]:
    """Create another user for testing."""
    user_data = {
        "email": "anotheruser@gmail.com",
        "password": "StrongPass123!"
    }
    stmt = select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.USER
    )
    result = await db_session.execute(stmt)
    user_group = result.scalars().first()

    user = UserModel.create(
        email=cast(EmailStr, user_data["email"]),
        raw_password=user_data["password"],
        group_id=user_group.id
    )
    user.is_active = True

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})

    headers = {"Authorization": f"Bearer {jwt_access_token}"}

    return {
        "user_id": user.id,
        "email": user.email,
        "password": user_data["password"],
        "access_token": jwt_access_token,
        "headers": headers
    }


@pytest_asyncio.fixture(scope="function")
async def seed_movies(db_session) -> list[dict[str, Any]]:
    """
    Seed movies into the database for testing.
    If movies already exist, return the first two.
    """
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

    movies = [
        MovieModel(
            name=f"Movie1",
            year=2020,
            time=120,
            imdb=7.0,
            votes=100,
            meta_score=75.0,
            gross=50000000.0,
            description="Desc1",
            price=Decimal(10.0),
            certification_id=1,

        ),
        MovieModel(
            name=f"Movie2",
            year=2021,
            time=90,
            imdb=8.0,
            votes=200,
            meta_score=85.0,
            gross=75000000.0,
            description="Desc2",
            price=Decimal(12.0),
            certification_id=1
        ),
    ]
    db_session.add_all(movies)
    await db_session.commit()
    for m in movies:
        await db_session.refresh(m)
    return [
        {
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
        } for m in movies
    ]


@pytest_asyncio.fixture(scope="function")
async def pending_order(
    db_session,
    activated_user,
    seed_movies
) -> dict[str, int | str]:
    """
    Create a pending order with order items for testing payments.
    The order includes the first two movies from the seeded movies.
    """
    movie_data1 = seed_movies[0]
    movie_data2 = seed_movies[1]

    order = OrderModel(
        user_id=activated_user["user_id"],
        status=OrderStatusEnum.PENDING,
        total_amount=Decimal(str(movie_data1["price"])) + Decimal(
            str(movie_data2["price"])
        )
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    order_item1 = OrderItemModel(
        order_id=order.id,
        movie_id=movie_data1["id"],
        price_at_order=Decimal(str(movie_data1["price"]))
    )
    order_item2 = OrderItemModel(
        order_id=order.id,
        movie_id=movie_data2["id"],
        price_at_order=Decimal(str(movie_data2["price"]))
    )
    db_session.add_all((order_item1, order_item2))
    await db_session.commit()
    await db_session.refresh(order_item1)
    await db_session.refresh(order_item2)

    return {
        "order_id": order.id,
        "total_amount": order.total_amount,
        "order_item1_id": order_item1.id,
        "order_item1_price": order_item1.price_at_order,
        "order_item2_id": order_item2.id,
        "order_item2_price": order_item2.price_at_order,
    }


@pytest_asyncio.fixture(scope="function")
async def mock_avatar() -> MagicMock:
    """Fixture for a mock avatar file."""
    img = Image.new("RGB", (10, 10), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "avatar.png"
    mock_file.content_type = "image/png"
    mock_file.file = img_byte_arr
    return mock_file


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_mailhog(request, settings):
    """Clear all messages from MailHog before each test."""
    if "e2e" in request.keywords:
        async with AsyncClient() as client:
            await client.delete(
                f"http://{settings.MAIL_SERVER}:8025/api/v1/messages"
            )
