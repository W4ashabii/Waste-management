# Waste Management MVP

A complete waste-segregation system with camera-based detection, truck management, and real-time alerts. Built with FastAPI, YOLOv8 (mock), and vanilla HTML/JS frontends.

## Features

- **Image Detection**: Upload images for waste classification (degradable/non-degradable)
- **Real-time Alerts**: WebSocket-based alerts for high-confidence detections
- **Truck Management**: Dispatch and track waste collection trucks
- **Role-based Access**: User, Ward Admin, and Municipality Admin roles
- **Analytics**: Ward-level waste detection analytics
- **Three Frontends**: User, Ward Admin, and Municipality Admin interfaces

## Tech Stack

- **Backend**: Python + FastAPI (async)
- **Database**: PostgreSQL (production) / SQLite (testing)
- **Model Service**: FastAPI microservice with YOLOv8 mock
- **Frontend**: Vanilla HTML + JavaScript
- **Real-time**: WebSocket
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed (for Docker deployment)
- Python 3.11+ (for local development)
- Port 8000, 8001, 5432, and 80 available

### Option 1: Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# The services will be available at:
# - Backend API: http://localhost:8000
# - Model Service: http://localhost:8001
# - Frontends: http://localhost:80/user/, http://localhost:80/ward/, http://localhost:80/municipality/
# - Database: localhost:5432
```

### Option 2: Run Locally (No Docker Networking)

If you encounter Docker networking issues, use the local development script:

```bash
# Run services locally using Python
./run_local.sh

# Services will be available at:
# - Backend API: http://localhost:8000
# - Model Service: http://localhost:8001
# - Frontends: Open HTML files directly in browser
```

### Seed the Database

```bash
# Run the seed script (from within the backend container)
docker-compose exec backend python seed_db.py
```

This creates:
- 1 municipality
- 3 wards
- 3 test users
- 2 trucks

## Test Accounts

| Role | Email | Password | Ward ID |
|------|-------|----------|---------|
| User | user@example.com | user123 | 1 |
| Ward Admin | ward@example.com | ward123 | 1 |
| Municipality Admin | municipality@example.com | muni123 | None |

## API Endpoints

### Authentication

#### Login
```bash
curl -X POST -F "username=user@example.com" -F "password=user123" \
  http://localhost:8000/api/v1/auth/login
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "Regular User",
    "role": "user",
    "ward_id": 1
  }
}
```

#### Register
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"New User","email":"new@example.com","password":"new123","role":"user"}' \
  http://localhost:8000/api/v1/auth/register
```

### Detection

#### Detect Waste
```bash
curl -X POST -F "image=@test.jpg" -F "camera_id=cam-1" \
  http://localhost:8000/api/v1/detect
```

Response:
```json
{
  "label": "degradable",
  "confidence": 0.92,
  "bboxes": [{"x": 0, "y": 0, "w": 100, "h": 200}],
  "detection_id": 123
}
```

### Trucks

#### List Trucks
```bash
curl -X GET -H "Authorization: Bearer <JWT>" \
  http://localhost:8000/api/v1/trucks
```

#### Dispatch Truck
```bash
curl -X POST -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" \
  -d '{"ward_id": 1, "alert_id": 1}' \
  http://localhost:8000/api/v1/trucks/1/dispatch
```

#### Update Truck State
```bash
curl -X POST -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" \
  -d '{"state": "enroute"}' \
  http://localhost:8000/api/v1/trucks/1/update_state
```

### Alerts

#### Get Alerts
```bash
curl -X GET -H "Authorization: Bearer <JWT>" \
  http://localhost:8000/api/v1/alerts
```

#### Get Alerts by Ward
```bash
curl -X GET -H "Authorization: Bearer <JWT>" \
  "http://localhost:8000/api/v1/alerts?ward_id=1"
```

### Analytics

#### Get Ward Analytics
```bash
curl -X GET -H "Authorization: Bearer <JWT>" \
  http://localhost:8000/api/v1/analytics/ward/1?range=7d
```

Response:
```json
[
  {
    "ward_id": 1,
    "date": "2024-01-15",
    "degradable_count": 15,
    "non_degradable_count": 8
  }
]
```

### WebSocket

#### Connect to Alerts WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alerts?token=<JWT>');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Alert:', data);
};
```

Message formats:
```json
// Alert created
{
  "type": "alert",
  "data": {
    "id": 1,
    "ward_id": 1,
    "detection_id": 123,
    "severity": "high",
    "label": "degradable",
    "confidence": 0.92
  }
}

// Truck state updated
{
  "type": "truck_update",
  "data": {
    "truck_id": 1,
    "state": "enroute",
    "ward_id": 1
  }
}
```

## Frontend Interfaces

### User Frontend
- URL: `http://localhost:80/user/`
- Features:
  - Upload images for waste detection
  - View detection results
  - See live alerts
  - Check truck information

### Ward Admin Frontend
- URL: `http://localhost:80/ward/`
- Features:
  - View alerts for assigned ward
  - Dispatch trucks to alerts
  - Update truck states
  - Monitor ward trucks
  - Real-time WebSocket updates

### Municipality Admin Frontend
- URL: `http://localhost:80/municipality/`
- Features:
  - View all wards and trucks
  - Reassign trucks between wards
  - View analytics across wards
  - Monitor system-wide alerts
  - Real-time WebSocket updates

## Database Schema

### Tables

- **municipalities**: `id`, `name`, `created_at`
- **wards**: `id`, `name`, `municipality_id`, `created_at`
- **users**: `id`, `name`, `email`, `password_hash`, `role`, `ward_id`, `created_at`
- **cameras**: `id`, `name`, `ward_id`, `location`, `last_seen`, `created_at`
- **trucks**: `id`, `plate_no`, `ward_id_assigned`, `state`, `last_location`, `capacity`, `created_at`
- **detection_records**: `id`, `camera_id`, `ward_id`, `image_url`, `label`, `confidence`, `bbox`, `timestamp`
- **alerts**: `id`, `ward_id`, `detection_id`, `severity`, `is_acknowledged`, `created_at`
- **truck_tasks**: `id`, `truck_id`, `ward_id`, `alert_id`, `state`, `dispatched_at`, `completed_at`, `created_at`

### Truck States
- `idle`: Truck available for dispatch
- `dispatched`: Truck assigned to a task
- `enroute`: Truck on the way to location
- `collecting`: Truck collecting waste
- `completed`: Task completed

### User Roles
- `user`: Regular user, can submit images
- `ward_admin`: Manages trucks for specific ward
- `municipality_admin`: Full system access

## Model Service

The model service runs on port 8001 and provides object detection:

### Detect Endpoint
```bash
curl -X POST -F "image=@test.jpg" \
  http://localhost:8001/detect
```

Response:
```json
{
  "predictions": [
    {
      "label": "plastic_bottle",
      "class_id": 3,
      "confidence": 0.94,
      "bbox": [10, 20, 100, 200]
    }
  ],
  "inference_ms": 120
}
```

### Label Mapping

The backend maps model labels to categories using `backend/app/label_mapping.json`:

```json
{
  "plastic_bottle": "non_degradable",
  "plastic_bag": "non_degradable",
  "metal_can": "non_degradable",
  "glass_bottle": "non_degradable",
  "food_waste": "degradable",
  "paper": "degradable",
  "cardboard": "degradable",
  "organic_waste": "degradable",
  "styrofoam": "non_degradable",
  "battery": "non_degradable"
}
```

## Testing

### Run Unit Tests
```bash
# Run tests from within the backend container
docker-compose exec backend pytest app/tests.py -v
```

### Test Coverage
The test suite covers:
- Authentication (login, register)
- Detection endpoint
- Truck management (list, dispatch, update state)
- Alerts retrieval
- Analytics
- Role-based access control

## Demo Verification Steps

1. **Start the system**
   ```bash
   docker-compose up --build
   ```

2. **Seed the database**
   ```bash
   docker-compose exec backend python seed_db.py
   ```

3. **Test authentication**
   ```bash
   # Login as user
   curl -X POST -F "username=user@example.com" -F "password=user123" \
     http://localhost:8000/api/v1/auth/login
   ```

4. **Test detection**
   ```bash
   # Create a test image file
   echo "test" > test.jpg
   
   # Submit for detection
   curl -X POST -F "image=@test.jpg" -F "camera_id=cam-1" \
     http://localhost:8000/api/v1/detect
   ```

5. **Test truck management**
   ```bash
   # Get JWT token first, then:
   TOKEN="your-jwt-token"
   
   # List trucks
   curl -X GET -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/trucks
   
   # Dispatch truck (as ward admin)
   curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"ward_id": 1, "alert_id": 1}' \
     http://localhost:8000/api/v1/trucks/1/dispatch
   ```

6. **Test frontends**
   - Open `http://localhost:80/user/` in browser
   - Open `http://localhost:80/ward/` in browser
   - Open `http://localhost:80/municipality/` in browser
   - Login with test credentials
   - Try submitting images, dispatching trucks, etc.

7. **Test WebSocket**
   - Open browser developer console
   - Connect to WebSocket and observe real-time updates
   - Submit a detection and see the alert appear in real-time

## Project Structure

```
/backend
  /app
    __init__.py
    config.py          # Configuration settings
    database.py        # Database connection and session
    models.py          # SQLAlchemy models
    auth.py            # Authentication and authorization
    main.py            # FastAPI application and endpoints
    label_mapping.json # Model label to category mapping
    tests.py           # Unit tests
  seed_db.py          # Database seeding script
  Dockerfile
  requirements.txt

/model-service
  /app
    __init__.py
    config.py          # Configuration settings
    main.py            # FastAPI model service
  Dockerfile
  requirements.txt

/frontend
  /user/index.html     # User frontend
  /ward/index.html     # Ward admin frontend
  /municipality/index.html  # Municipality admin frontend

docker-compose.yml
nginx.conf
README.md
```

## Development Notes

### Adding Real YOLOv8 Model

1. Replace the mock inference in `model-service/app/main.py`:
   ```python
   from ultralytics import YOLO
   model = YOLO("yolov8n.pt")
   
   # In the detect endpoint:
   results = model(img)
   # Process results and return predictions
   ```

2. Update `label_mapping.json` with your model's labels

3. Set `MOCK_MODE=false` in model-service environment

### Customizing Alert Thresholds

Modify the threshold logic in `backend/app/main.py` in the `/detect` endpoint:
```python
# Current: confidence > 0.7
if confidence > 0.7:
    # Create alert
```

### Adding New Ward/Municipality Endpoints

The current MVP focuses on trucks and detection. To add full CRUD for wards and municipalities, add standard FastAPI endpoints following the existing patterns.

## Troubleshooting

### Docker Networking Issues
If you encounter "operation not supported" errors with Docker networking:
- Use the local development script: `./run_local.sh`
- Or try restarting Docker: `sudo systemctl restart docker`
- Check Docker daemon logs: `sudo journalctl -u docker`

### Database Connection Issues
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Check database logs: `docker-compose logs db`
- For local mode, ensure PostgreSQL is running and database exists

### Model Service Unreachable
- Verify model-service is running: `curl http://localhost:8001/health`
- Check model-service logs: `docker-compose logs model-service`
- For local mode, check if the Python process is running

### WebSocket Connection Failed
- Ensure backend is running: `curl http://localhost:8000/api/v1/health`
- Check firewall settings for WebSocket connections
- Verify backend logs for WebSocket connection errors

### Frontend Not Loading
- Ensure nginx is running: `docker-compose ps nginx`
- Check nginx configuration in `nginx.conf`
- For local mode, open HTML files directly in browser

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Architecture Documentation](docs/ARCHITECTURE.md)** - System design and component architecture
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[Code Guardrails](docs/GUARDRAILS.md)** - Development standards and best practices
- **[Testing Guide](docs/TESTING_GUIDE.md)** - Comprehensive testing guide

## Testing

The project includes a comprehensive test suite in the `tests/` directory:

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

See [tests/README.md](tests/README.md) for detailed testing information.

## License

This is an MVP project for demonstration purposes.

## Future Enhancements

- Real YOLOv8 model integration
- Image storage (S3/local)
- Email/SMS notifications
- Mobile app
- Advanced analytics dashboard
- Geolocation tracking for trucks
- Historical data analysis
- Integration with waste collection schedules
