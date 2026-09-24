# Tests Directory

This directory contains the test suite for the Waste Management System.

## Test Files

- `conftest.py` - Pytest configuration and shared fixtures
- `test_auth.py` - Authentication and authorization tests
- `test_detection.py` - Waste detection endpoint tests
- `test_trucks.py` - Truck management tests
- `test_alerts.py` - Alert system tests
- `test_analytics.py` - Analytics endpoint tests

## Running Tests

### Quick Start
```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Test Organization

Tests are organized by feature and functionality:

1. **Authentication Tests** (`test_auth.py`)
   - Login functionality
   - User registration
   - Token validation
   - Permission checks

2. **Detection Tests** (`test_detection.py`)
   - Image upload
   - Detection processing
   - Alert creation
   - Label mapping

3. **Truck Tests** (`test_trucks.py`)
   - Truck listing
   - Truck dispatching
   - State transitions
   - Permission validation

4. **Alert Tests** (`test_alerts.py`)
   - Alert retrieval
   - Alert filtering
   - WebSocket notifications
   - Alert acknowledgment

5. **Analytics Tests** (`test_analytics.py`)
   - Ward analytics
   - Data aggregation
   - Permission checks
   - Date range filtering

## Test Fixtures

Available fixtures in `conftest.py`:

- `setup_database` - Session-scoped database setup with seed data (autouse)
- `mock_model_service` - Mocks the external model-service API for detection tests
- `db_session` - Database session for tests
- `test_client` - HTTP client for API testing
- `authenticated_user_client` - Pre-authenticated user client
- `authenticated_ward_admin_client` - Pre-authenticated ward admin client
- `authenticated_municipality_admin_client` - Pre-authenticated municipality admin client
- `sample_detection_data` - Sample detection data
- `sample_truck_data` - Sample truck data

## Test Data

Tests use a separate SQLite database (`test.db`) to avoid affecting development data. The database is created, seeded with test users/wards/trucks, and destroyed automatically during test execution. Seeded credentials:

- User: `user@example.com` / `user123` (ward 1)
- Ward Admin: `ward@example.com` / `ward123` (ward 1)
- Municipality Admin: `municipality@example.com` / `muni123`

## Coverage Goals

- Overall coverage: 70%+
- Critical path coverage: 100%
- Business logic coverage: 90%+
- API endpoint coverage: 80%+

## Continuous Integration

Tests are configured to run automatically on CI/CD pipelines. See the main project documentation for CI/CD configuration.

## Adding New Tests

When adding new tests:

1. Follow the existing test structure
2. Use descriptive test names
3. Follow the Arrange-Act-Assert pattern
4. Add appropriate fixtures if needed
5. Update this README if adding new test files
6. Ensure tests are independent and repeatable

## Troubleshooting

### Tests Fail Due to Database
```bash
rm test.db
pytest
```

### Import Errors
```bash
# Ensure you're running from project root
cd /path/to/project
pytest
```

### Async Test Issues
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Guide](../docs/TESTING_GUIDE.md)
- [API Documentation](../docs/API_DOCUMENTATION.md)
