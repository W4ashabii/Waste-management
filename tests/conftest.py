"""
Pytest configuration and fixtures for the waste management system.
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
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


async def seed_test_data():
    """Seed municipality, wards, users, and trucks for tests."""
    async with async_session() as session:
        municipality = Municipality(name="Default Municipality")
        session.add(municipality)
        await session.commit()
        await session.refresh(municipality)

        ward1 = Ward(name="Ward 1", municipality_id=municipality.id)
        ward2 = Ward(name="Ward 2", municipality_id=municipality.id)
        ward3 = Ward(name="Ward 3", municipality_id=municipality.id)
        session.add_all([ward1, ward2, ward3])
        await session.commit()
        await session.refresh(ward1)
        await session.refresh(ward2)
        await session.refresh(ward3)

        user1 = User(
            name="Regular User",
            email="user@example.com",
            password_hash=get_password_hash("user123"),
            role=UserRole.USER,
            ward_id=ward1.id
        )
        ward_admin = User(
            name="Ward Admin",
            email="ward@example.com",
            password_hash=get_password_hash("ward123"),
            role=UserRole.WARD_ADMIN,
            ward_id=ward1.id
        )
        municipality_admin = User(
            name="Municipality Admin",
            email="municipality@example.com",
            password_hash=get_password_hash("muni123"),
            role=UserRole.MUNICIPALITY_ADMIN
        )
        session.add_all([user1, ward_admin, municipality_admin])
        await session.commit()

        truck1 = Truck(
            plate_no="TRUCK-001",
            ward_id_assigned=ward1.id,
            state=TruckState.IDLE,
            capacity=100
        )
        truck2 = Truck(
            plate_no="TRUCK-002",
            ward_id_assigned=ward2.id,
            state=TruckState.IDLE,
            capacity=150
        )
        session.add_all([truck1, truck2])
        await session.commit()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Create tables and seed data once per test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed_test_data()
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_model_service(monkeypatch):
    """Mock the model-service HTTP call used by the /detect endpoint.

    Only intercepts requests to the model service URL so the ASGI test
    client keeps working normally. Returns a fixed prediction.
    """
    from app.config import settings
    original_post = httpx.AsyncClient.post

    class FakeResponse:
        def json(self):
            return {
                "predictions": [
                    {
                        "label": "plastic_bottle",
                        "confidence": 0.9,
                        "bbox": [10, 20, 100, 200],
                    }
                ]
            }

    async def fake_post(self, url, **kwargs):
        if url.startswith(f"{settings.MODEL_SERVICE_URL}/detect"):
            return FakeResponse()
        return await original_post(self, url, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return fake_post


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