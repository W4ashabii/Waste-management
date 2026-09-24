"""
Analytics endpoint tests for the waste management system.
Tests ward-level analytics and data aggregation.
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_analytics_as_municipality_admin():
    """Test getting analytics as municipality admin."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as municipality admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "municipality@example.com", "password": "muni123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/analytics/ward/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        analytics = response.json()
        assert isinstance(analytics, list)


@pytest.mark.asyncio
async def test_get_analytics_as_ward_admin():
    """Test getting analytics as ward admin for own ward."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as ward admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "ward@example.com", "password": "ward123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/analytics/ward/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        analytics = response.json()
        assert isinstance(analytics, list)


@pytest.mark.asyncio
async def test_get_analytics_unauthorized_ward():
    """Test that ward admin cannot access other ward's analytics."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as ward admin (ward 1)
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "ward@example.com", "password": "ward123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access ward 2 analytics
        response = await client.get(
            "/api/v1/analytics/ward/2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_analytics_unauthorized_user():
    """Test that regular user cannot access analytics."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "user123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/analytics/ward/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_analytics_with_date_range():
    """Test analytics with date range parameter."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as municipality admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "municipality@example.com", "password": "muni123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/analytics/ward/1?range=7d",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        analytics = response.json()
        assert isinstance(analytics, list)


@pytest.mark.asyncio
async def test_analytics_response_structure():
    """Test that analytics response has correct structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as municipality admin
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "municipality@example.com", "password": "muni123"}
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/analytics/ward/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        analytics = response.json()
        
        # Check structure of analytics items
        for item in analytics:
            assert "ward_id" in item
            assert "date" in item
            assert "degradable_count" in item
            assert "non_degradable_count" in item
