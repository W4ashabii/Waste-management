"""
Detection endpoint tests for the waste management system.
Tests image upload, detection, and alert creation.
"""
import pytest
import io
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_detection_endpoint():
    """Test waste detection with image upload."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a minimal test image
        image_content = b"fake image content"
        image_file = io.BytesIO(image_content)
        image_file.name = "test.jpg"
        
        files = {"image": ("test.jpg", image_file, "image/jpeg")}
        data = {"camera_id": "test-camera"}
        
        response = await client.post("/api/v1/detect", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert "label" in result
        assert result["label"] in ["degradable", "non_degradable"]
        assert "confidence" in result
        assert "detection_id" in result
        assert "bboxes" in result


@pytest.mark.asyncio
async def test_detection_without_camera_id():
    """Test detection without providing camera ID."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        image_content = b"fake image content"
        image_file = io.BytesIO(image_content)
        image_file.name = "test.jpg"
        
        files = {"image": ("test.jpg", image_file, "image/jpeg")}
        
        response = await client.post("/api/v1/detect", files=files)
        assert response.status_code == 200
        result = response.json()
        assert "label" in result


@pytest.mark.asyncio
async def test_detection_creates_alert():
    """Test that high-confidence detection creates an alert."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First login to get token
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "user123"}
        )
        token = login_response.json()["access_token"]
        
        # Submit detection
        image_content = b"fake image content"
        image_file = io.BytesIO(image_content)
        image_file.name = "test.jpg"
        
        files = {"image": ("test.jpg", image_file, "image/jpeg")}
        data = {"camera_id": "alert-test-camera"}
        
        detection_response = await client.post("/api/v1/detect", files=files, data=data)
        assert detection_response.status_code == 200
        
        # Check if alert was created (confidence > 0.7)
        if detection_response.json()["confidence"] > 0.7:
            alerts_response = await client.get(
                "/api/v1/alerts",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert alerts_response.status_code == 200
            alerts = alerts_response.json()
            # Should have at least one alert
            assert len(alerts) > 0
