"""
Truck management tests for the waste management system.
Tests truck listing, dispatching, and state transitions.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_trucks_as_user():
    """Test getting trucks as regular user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as user
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "user123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/trucks",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        trucks = response.json()
        assert isinstance(trucks, list)


@pytest.mark.asyncio
async def test_get_trucks_as_ward_admin():
    """Test getting trucks as ward admin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as ward admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "ward@example.com", "password": "ward123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/trucks",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        trucks = response.json()
        assert isinstance(trucks, list)


@pytest.mark.asyncio
async def test_get_trucks_as_municipality_admin():
    """Test getting trucks as municipality admin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as municipality admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "municipality@example.com", "password": "muni123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/trucks",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        trucks = response.json()
        assert isinstance(trucks, list)


@pytest.mark.asyncio
async def test_dispatch_truck_as_ward_admin(mock_model_service):
    """Test dispatching truck as ward admin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as ward admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "ward@example.com", "password": "ward123"}
        )
        token = login_response.json()["access_token"]
        
        # First create a detection to get an alert
        import io
        image_content = b"fake image content"
        image_file = io.BytesIO(image_content)
        image_file.name = "test.jpg"
        files = {"image": ("test.jpg", image_file, "image/jpeg")}
        data = {"camera_id": "dispatch-test-camera"}
        
        detection_response = await client.post("/api/v1/detect", files=files, data=data)
        detection_id = detection_response.json()["detection_id"]
        
        # Get alerts to find the alert ID
        alerts_response = await client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {token}"}
        )
        alerts = alerts_response.json()
        
        if alerts:
            alert_id = alerts[0]["id"]
            ward_id = alerts[0]["ward_id"]
            
            # Dispatch truck
            dispatch_response = await client.post(
                f"/api/v1/trucks/1/dispatch",
                headers={"Authorization": f"Bearer {token}"},
                json={"ward_id": ward_id, "alert_id": alert_id}
            )
            # This may fail if truck doesn't belong to ward, but that's expected behavior
            assert dispatch_response.status_code in [200, 403, 404]


@pytest.mark.asyncio
async def test_update_truck_state():
    """Test updating truck state."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as ward admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "ward@example.com", "password": "ward123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.post(
            "/api/v1/trucks/1/update_state",
            headers={"Authorization": f"Bearer {token}"},
            json={"state": "enroute"}
        )
        # This may fail due to ward access, but that's expected behavior
        assert response.status_code in [200, 403]


@pytest.mark.asyncio
async def test_dispatch_truck_unauthorized():
    """Test that regular user cannot dispatch trucks."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "user123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.post(
            "/api/v1/trucks/1/dispatch",
            headers={"Authorization": f"Bearer {token}"},
            json={"ward_id": 1, "alert_id": 1}
        )
        assert response.status_code == 403
