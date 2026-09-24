"""
Pytest configuration and fixtures for the waste management system.
"""
import pytest
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from app.main import app
from app.database import get_db
from app.models import Base
from app.auth import get_password_hash
from app.models import User, Ward, Municipality, Truck, UserRole, TruckState


# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with async_session() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
async def setup_database():
    """Setup test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database):
    """Provide database session for tests."""
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_client():
    """Provide test client for API tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_user_client(test_client):
    """Provide authenticated client as regular user."""
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "user@example.com", "password": "user123"}
    )
    token = login_response.json()["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    yield test_client


@pytest.fixture
async def authenticated_ward_admin_client(test_client):
    """Provide authenticated client as ward admin."""
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "ward@example.com", "password": "ward123"}
    )
    token = login_response.json()["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    yield test_client


@pytest.fixture
async def authenticated_municipality_admin_client(test_client):
    """Provide authenticated client as municipality admin."""
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "municipality@example.com", "password": "muni123"}
    )
    token = login_response.json()["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    yield test_client


@pytest.fixture
async def sample_detection_data():
    """Provide sample detection data for testing."""
    return {
        "label": "degradable",
        "confidence": 0.85,
        "bboxes": [{"x": 10, "y": 20, "w": 100, "h": 200}]
    }


@pytest.fixture
async def sample_truck_data():
    """Provide sample truck data for testing."""
    return {
        "plate_no": "TEST-001",
        "ward_id_assigned": 1,
        "state": "idle",
        "capacity": 100
    }
