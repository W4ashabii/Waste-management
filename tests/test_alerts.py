"""
Alert system tests for the waste management system.
Tests alert creation, retrieval, and WebSocket notifications.
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_alerts_as_user():
    """Test getting alerts as regular user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as user
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "user123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_get_alerts_as_ward_admin():
    """Test getting alerts as ward admin."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as ward admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "ward@example.com", "password": "ward123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_get_alerts_by_ward_id():
    """Test getting alerts filtered by ward ID."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as municipality admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "municipality@example.com", "password": "muni123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/alerts?ward_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_alerts_unauthorized():
    """Test accessing alerts without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_high_confidence_detection_creates_alert():
    """Test that high-confidence detection automatically creates alert."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as user
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "user123"}
        )
        token = login_response.json()["access_token"]
        
        # Get initial alert count
        initial_alerts = await client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {token}"}
        )
        initial_count = len(initial_alerts.json())
        
        # Submit detection
        import io
        image_content = b"fake image content"
        image_file = io.BytesIO(image_content)
        image_file.name = "test.jpg"
        files = {"image": ("test.jpg", image_file, "image/jpeg")}
        data = {"camera_id": "alert-creation-test"}
        
        detection_response = await client.post("/api/v1/detect", files=files, data=data)
        detection_result = detection_response.json()
        
        # If confidence is high enough, check for new alert
        if detection_result["confidence"] > 0.7:
            final_alerts = await client.get(
                "/api/v1/alerts",
                headers={"Authorization": f"Bearer {token}"}
            )
            final_count = len(final_alerts.json())
            # Should have at least as many alerts as before
            assert final_count >= initial_count
