"""Pytest fixtures. Each test gets a freshly seeded SQLite database."""
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SEED_ON_STARTUP"] = "false"
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import async_session, engine
from app.main import app
from app.models import Base
from app.seed import seed

DEMO_PASSWORD = "demo1234"
KMC_EMAIL = "anita.shrestha@kathmandu.gov.np"
WARD_EMAIL = "ward17@kathmandu.gov.np"


@pytest.fixture(autouse=True)
async def database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as db:
        await seed(db)
    yield


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client():
    async with make_client() as c:
        yield c


async def login(client: AsyncClient, email: str, portal: str) -> AsyncClient:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD, "portal": portal})
    assert r.status_code == 200, r.text
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client


@pytest.fixture
async def kmc():
    async with make_client() as c:
        yield await login(c, KMC_EMAIL, "kmc")


@pytest.fixture
async def ward():
    async with make_client() as c:
        yield await login(c, WARD_EMAIL, "ward")


@pytest.fixture
def fake_classifier(monkeypatch):
    """Replace the model-service call with a fixed prediction."""
    calls = []

    async def fake(data, filename, content_type):
        calls.append(filename)
        return {"label": "Bio", "category": "degradable", "confidence": 0.97,
                "probabilities": {"Bio": 0.97, "Non_Bio": 0.03}, "inference_ms": 12}

    monkeypatch.setattr("app.routers.identify.classify", fake)
    return calls
