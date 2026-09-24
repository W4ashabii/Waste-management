# Waste Management API Documentation

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.waste-management.com`

## Authentication

All protected endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### Authentication

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
username=user@example.com&password=user123
```

**Response (200 OK):**
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
```http
POST /api/v1/auth/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "New User",
  "email": "new@example.com",
  "password": "securepassword",
  "role": "user",
  "ward_id": 1
}
```

**Response (200 OK):**
```json
{
  "message": "User created successfully",
  "user_id": 4
}
```

### Detection

#### Detect Waste
```http
POST /api/v1/detect
Content-Type: multipart/form-data
```

**Request Body:**
- `image`: Image file (required)
- `camera_id`: Camera identifier (optional)

**Response (200 OK):**
```json
{
  "label": "degradable",
  "confidence": 0.92,
  "bboxes": [
    {
      "x": 10,
      "y": 20,
      "w": 100,
      "h": 200
    }
  ],
  "detection_id": 123
}
```

**Label Values:**
- `degradable`: Organic waste, paper, cardboard
- `non_degradable`: Plastic, metal, glass, electronics

### Trucks

#### List Trucks
```http
GET /api/v1/trucks
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "plate_no": "TRUCK-001",
    "ward_id_assigned": 1,
    "state": "idle",
    "last_location": null,
    "capacity": 100
  }
]
```

**Truck States:**
- `idle`: Available for dispatch
- `dispatched`: Assigned to task
- `enroute`: Traveling to location
- `collecting`: Collecting waste
- `completed`: Task finished

#### Dispatch Truck
```http
POST /api/v1/trucks/{truck_id}/dispatch
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "ward_id": 1,
  "alert_id": 5
}
```

**Response (200 OK):**
```json
{
  "message": "Truck dispatched successfully"
}
```

**Permissions:**
- Ward Admin: Can dispatch trucks in their ward
- Municipality Admin: Can dispatch any truck
- User: Not authorized

#### Update Truck State
```http
POST /api/v1/trucks/{truck_id}/update_state
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "state": "enroute"
}
```

**Response (200 OK):**
```json
{
  "message": "Truck state updated successfully"
}
```

### Alerts

#### Get Alerts
```http
GET /api/v1/alerts
Authorization: Bearer <token>
```

**Query Parameters:**
- `ward_id`: Filter by ward ID (optional)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "ward_id": 1,
    "detection_id": 123,
    "severity": "high",
    "is_acknowledged": false,
    "created_at": "2024-01-15T10:30:00"
  }
]
```

**Severity Levels:**
- `high`: Confidence > 0.9
- `medium`: Confidence > 0.7
- `low`: Confidence ≤ 0.7

### Analytics

#### Get Ward Analytics
```http
GET /api/v1/analytics/ward/{ward_id}
Authorization: Bearer <token>
```

**Query Parameters:**
- `range`: Time range (default: "7d")

**Response (200 OK):**
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

**Permissions:**
- Municipality Admin: Access all wards
- Ward Admin: Access own ward only
- User: Not authorized

### WebSocket

#### Alert Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alerts?token=<jwt_token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

**Message Types:**

**Alert Created:**
```json
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
```

**Truck Update:**
```json
{
  "type": "truck_update",
  "data": {
    "truck_id": 1,
    "state": "enroute",
    "ward_id": 1
  }
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized as ward admin"
}
```

### 404 Not Found
```json
{
  "detail": "Truck not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Rate Limiting

Currently not implemented in MVP. Planned for production:
- 100 requests per minute per user
- 1000 requests per minute per IP

## Versioning

Current API version: `v1`

URL format: `/api/v1/{resource}`

## Pagination

Currently not implemented in MVP. Planned for production:
- `?page=1&limit=20`
- Response includes pagination metadata

## Filtering and Sorting

Currently limited implementation. Planned enhancements:
- Advanced filtering on list endpoints
- Multiple sort options
- Date range queries
