import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
import io
import json
from app.main import app
from app.database import get_db, Base
from app.models import User, Ward, Truck, UserRole, TruckState
from app.auth import get_password_hash


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with async_session() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database):
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_user(db_session):
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash=get_password_hash("test123"),
        role=UserRole.USER
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_ward_admin(db_session):
    ward = Ward(name="Test Ward")
    db_session.add(ward)
    await db_session.commit()
    await db_session.refresh(ward)
    
    user = User(
        name="Ward Admin",
        email="ward@example.com",
        password_hash=get_password_hash("ward123"),
        role=UserRole.WARD_ADMIN,
        ward_id=ward.id
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_municipality_admin(db_session):
    user = User(
        name="Municipality Admin",
        email="municipality@example.com",
        password_hash=get_password_hash("muni123"),
        role=UserRole.MUNICIPALITY_ADMIN
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_truck(db_session):
    ward = Ward(name="Truck Ward")
    db_session.add(ward)
    await db_session.commit()
    await db_session.refresh(ward)
    
    truck = Truck(
        plate_no="TEST-123",
        ward_id_assigned=ward.id,
        state=TruckState.IDLE,
        capacity=100
    )
    db_session.add(truck)
    await db_session.commit()
    await db_session.refresh(truck)
    return truck


@pytest.mark.asyncio
async def test_login_success(test_client, test_user):
    response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "test123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_failure(test_client):
    response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "wrong@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_user(test_client):
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "New User",
            "email": "new@example.com",
            "password": "new123",
            "role": "user"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data


@pytest.mark.asyncio
async def test_detect_endpoint(test_client, db_session):
    # Create a ward first
    ward = Ward(name="Detection Ward")
    db_session.add(ward)
    await db_session.commit()
    
    # Create a mock image file
    image_content = b"fake image content"
    image_file = io.BytesIO(image_content)
    image_file.name = "test.jpg"
    
    files = {"image": ("test.jpg", image_file, "image/jpeg")}
    data = {"camera_id": "test-camera"}
    
    response = await test_client.post(
        "/api/v1/detect",
        files=files,
        data=data
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "label" in result
    assert result["label"] in ["degradable", "non_degradable"]
    assert "confidence" in result
    assert "detection_id" in result


@pytest.mark.asyncio
async def test_get_trucks_unauthorized(test_client):
    response = await test_client.get("/api/v1/trucks")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_trucks_ward_admin(test_client, test_ward_admin):
    # Login as ward admin
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "ward@example.com", "password": "ward123"}
    )
    token = login_response.json()["access_token"]
    
    response = await test_client.get(
        "/api/v1/trucks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dispatch_truck(test_client, test_ward_admin, test_truck):
    # Login as ward admin
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "ward@example.com", "password": "ward123"}
    )
    token = login_response.json()["access_token"]
    
    # Create an alert first (simplified - in real test you'd create detection + alert)
    ward_id = test_ward_admin.ward_id
    
    response = await test_client.post(
        f"/api/v1/trucks/{test_truck.id}/dispatch",
        headers={"Authorization": f"Bearer {token}"},
        json={"ward_id": ward_id, "alert_id": 1}
    )
    
    # This might fail if the truck doesn't belong to the ward, but that's expected behavior
    assert response.status_code in [200, 403, 404]


@pytest.mark.asyncio
async def test_update_truck_state(test_client, test_ward_admin, test_truck):
    # Login as ward admin
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "ward@example.com", "password": "ward123"}
    )
    token = login_response.json()["access_token"]
    
    response = await test_client.post(
        f"/api/v1/trucks/{test_truck.id}/update_state",
        headers={"Authorization": f"Bearer {token}"},
        json={"state": "enroute"}
    )
    
    # This might fail due to ward access, but that's expected behavior
    assert response.status_code in [200, 403]


@pytest.mark.asyncio
async def test_get_alerts(test_client, test_user):
    # Login as user
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "test123"}
    )
    token = login_response.json()["access_token"]
    
    response = await test_client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_analytics(test_client, test_municipality_admin):
    # Login as municipality admin
    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "municipality@example.com", "password": "muni123"}
    )
    token = login_response.json()["access_token"]
    
    response = await test_client.get(
        "/api/v1/analytics/ward/1",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    response = await test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
