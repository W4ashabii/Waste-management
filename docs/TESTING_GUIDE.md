# Testing Guide for Waste Management System

## Overview

This guide provides comprehensive information about testing the Waste Management System, including test setup, execution, and best practices.

## Test Structure

```
tests/
├── conftest.py           # Pytest configuration and fixtures
├── test_auth.py          # Authentication tests
├── test_detection.py     # Detection endpoint tests
├── test_trucks.py        # Truck management tests
├── test_alerts.py        # Alert system tests
└── test_analytics.py     # Analytics endpoint tests
```

## Prerequisites

### Required Packages
```bash
pip install pytest pytest-asyncio httpx
```

### Test Database
Tests use a separate SQLite database (`test.db`) to avoid affecting development data.

## Running Tests

### Run All Tests
```bash
# From project root
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_auth.py -v
```

### Run Specific Test
```bash
pytest tests/test_auth.py::test_login_success -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Tests in Parallel
```bash
pytest tests/ -n auto
```

## Test Fixtures

### Database Setup
```python
@pytest.fixture(scope="module")
async def setup_database():
    """Setup test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

### Authenticated Clients
```python
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
```

## Test Categories

### Unit Tests

**Purpose**: Test individual functions and methods in isolation.

**Example**:
```python
def test_password_hashing():
    """Test password hashing function."""
    password = "test123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)
```

### Integration Tests

**Purpose**: Test interactions between components.

**Example**:
```python
@pytest.mark.asyncio
async def test_detection_creates_alert():
    """Test that detection creates alert when confidence is high."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Submit detection
        response = await client.post("/api/v1/detect", files=files)
        # Verify alert was created
        alerts = await client.get("/api/v1/alerts")
        assert len(alerts.json()) > 0
```

### End-to-End Tests

**Purpose**: Test complete user workflows.

**Example**:
```python
@pytest.mark.asyncio
async def test_complete_truck_dispatch_workflow():
    """Test complete truck dispatch workflow."""
    # 1. Login as ward admin
    # 2. Submit detection
    # 3. Get alert
    # 4. Dispatch truck
    # 5. Verify truck state
    # 6. Verify WebSocket update
```

## Writing Tests

### Test Structure
```python
@pytest.mark.asyncio
async def test_descriptive_name():
    """Test description."""
    # Arrange
    test_data = prepare_test_data()
    
    # Act
    result = await perform_action(test_data)
    
    # Assert
    assert result.status_code == 200
    assert result.json()["expected_field"] == "expected_value"
```

### Best Practices

1. **Descriptive Names**: Use descriptive test names that explain what is being tested
2. **AAA Pattern**: Follow Arrange-Act-Assert pattern
3. **Independence**: Tests should be independent of each other
4. **Fast**: Tests should run quickly
5. **Clear**: Tests should be easy to understand

### Common Patterns

#### Testing API Endpoints
```python
@pytest.mark.asyncio
async def test_api_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/endpoint")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

#### Testing Authentication
```python
@pytest.mark.asyncio
async def test_protected_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Without token
        response = await client.get("/api/v1/protected")
        assert response.status_code == 401
        
        # With token
        token = await get_auth_token()
        response = await client.get(
            "/api/v1/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
```

#### Testing Database Operations
```python
@pytest.mark.asyncio
async def test_database_operation(db_session):
    # Create test data
    user = User(name="Test", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    
    # Verify creation
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    assert result.scalar_one_or_none() is not None
```

## Test Data Management

### Fixtures for Test Data
```python
@pytest.fixture
async def sample_user():
    """Provide sample user for testing."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "test123",
        "role": "user"
    }
```

### Database Cleanup
```python
@pytest.fixture
async def db_session(setup_database):
    """Provide database session with automatic cleanup."""
    async with async_session() as session:
        yield session
        await session.rollback()
```

## Mocking and Patching

### Mocking External Services
```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mock():
    with patch('app.external_service.call', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"result": "success"}
        
        result = await function_that_calls_external_service()
        
        mock_call.assert_called_once()
        assert result == {"result": "success"}
```

### Mocking Model Service
```python
@pytest.mark.asyncio
async def test_detection_with_mocked_model():
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value.json.return_value = {
            "predictions": [{"label": "plastic_bottle", "confidence": 0.9}]
        }
        
        response = await client.post("/api/v1/detect", files=files)
        assert response.status_code == 200
```

## WebSocket Testing

### Basic WebSocket Test
```python
@pytest.mark.asyncio
async def test_websocket_connection():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.websocket_connect("/ws/alerts") as websocket:
            await websocket.send_json({"type": "ping"})
            response = await websocket.receive_json()
            assert response["type"] == "pong"
```

### WebSocket Event Testing
```python
@pytest.mark.asyncio
async def test_websocket_alert_broadcast():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.websocket_connect("/ws/alerts") as websocket:
            # Trigger alert creation
            await client.post("/api/v1/detect", files=files)
            
            # Receive alert via WebSocket
            alert = await websocket.receive_json()
            assert alert["type"] == "alert"
```

## Performance Testing

### Response Time Testing
```python
@pytest.mark.asyncio
async def test_response_time():
    import time
    
    start_time = time.time()
    response = await client.get("/api/v1/trucks")
    end_time = time.time()
    
    assert end_time - start_time < 0.5  # 500ms max
    assert response.status_code == 200
```

### Load Testing
```python
@pytest.mark.asyncio
async def test_concurrent_requests():
    import asyncio
    
    async def make_request():
        return await client.get("/api/v1/trucks")
    
    responses = await asyncio.gather(*[make_request() for _ in range(10)])
    
    for response in responses:
        assert response.status_code == 200
```

## Error Testing

### Expected Error Testing
```python
@pytest.mark.asyncio
async def test_invalid_input():
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "invalid", "password": "invalid"}
    )
    assert response.status_code == 401
```

### Exception Testing
```python
@pytest.mark.asyncio
async def test_exception_handling():
    with pytest.raises(ValueError):
        await function_that_raises_value_error()
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx pytest-cov
      - name: Run tests
        run: pytest tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

#### Tests Fail Due to Database
```bash
# Remove test database and retry
rm test.db
pytest tests/ -v
```

#### Async Tests Hang
```bash
# Increase timeout
pytest tests/ --timeout=30
```

#### Import Errors
```bash
# Ensure you're running from project root
cd /path/to/project
pytest tests/ -v
```

## Test Metrics

### Coverage Goals
- **Overall Coverage**: 70%+
- **Critical Path Coverage**: 100%
- **Business Logic Coverage**: 90%+
- **API Endpoint Coverage**: 80%+

### Performance Targets
- **Test Execution Time**: < 2 minutes for full suite
- **Individual Test Time**: < 5 seconds per test
- **Setup Time**: < 10 seconds for test setup

## Best Practices Summary

1. **Write Tests First**: Consider TDD approach
2. **Keep Tests Simple**: Avoid complex test logic
3. **Use Descriptive Names**: Make tests self-documenting
4. **Test Edge Cases**: Don't just test happy paths
5. **Mock External Dependencies**: Isolate system under test
6. **Clean Up Resources**: Use fixtures for cleanup
7. **Run Tests Frequently**: Catch issues early
8. **Maintain Test Independence**: Tests shouldn't depend on each other
9. **Review Test Coverage**: Regularly check coverage reports
10. **Update Tests with Code**: Keep tests in sync with code changes

## Resources

### Documentation
- [Pytest Documentation](https://docs.pytest.org/)
- [Async Testing with Pytest](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

### Tools
- [pytest](https://github.com/pytest-dev/pytest)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [pytest-cov](https://github.com/pytest-dev/pytest-cov)
- [httpx](https://www.python-httpx.org/)
