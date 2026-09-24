"""
Authentication tests for the waste management system.
Tests login, registration, and JWT token validation.
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login with valid credentials."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "user123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_new_user():
    """Test user registration."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test User",
                "email": "testuser@example.com",
                "password": "testpass123",
                "role": "user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data


@pytest.mark.asyncio
async def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/trucks")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token():
    """Test accessing protected endpoint with invalid token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/trucks",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
