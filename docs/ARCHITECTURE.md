# Waste Management System Architecture

## System Overview

The Waste Management MVP is a microservices-based system for waste segregation detection and truck management. It consists of three main components:

1. **Backend API** - FastAPI-based REST API with authentication and business logic
2. **Model Service** - YOLOv8 inference microservice for waste detection
3. **Frontend** - Three vanilla HTML/JS interfaces for different user roles

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Frontend │     │  Ward Frontend  │     │ Mun. Frontend   │
│   (HTML/JS)     │     │   (HTML/JS)     │     │   (HTML/JS)     │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │ WebSocket              │ WebSocket              │ WebSocket
         │ HTTP/REST              │ HTTP/REST              │ HTTP/REST
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      Backend API          │
                    │      (FastAPI)            │
                    │  - Authentication          │
                    │  - Business Logic          │
                    │  - Database Operations     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │    Model Service          │
                    │    (FastAPI)              │
                    │  - YOLOv8 Inference       │
                    │  - Label Mapping          │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      Database             │
                    │   (PostgreSQL/SQLite)     │
                    └───────────────────────────┘
```

## Component Details

### Backend API

**Technology Stack:**
- Python 3.11+
- FastAPI (async web framework)
- SQLAlchemy + SQLModel (ORM)
- PostgreSQL (production) / SQLite (development)
- JWT (authentication)
- WebSocket (real-time updates)

**Key Responsibilities:**
- User authentication and authorization
- API request handling and validation
- Business logic implementation
- Database operations
- WebSocket connection management
- Alert broadcasting

**Key Modules:**
- `app/main.py` - FastAPI application and endpoints
- `app/auth.py` - Authentication and authorization
- `app/models.py` - Database models
- `app/database.py` - Database connection management
- `app/config.py` - Configuration settings

### Model Service

**Technology Stack:**
- Python 3.11+
- FastAPI (async web framework)
- YOLOv8 (computer vision model)
- PyTorch/ONNX (model runtime)

**Key Responsibilities:**
- Image receiving and preprocessing
- YOLOv8 model inference
- Label to category mapping
- Response formatting

**Key Features:**
- Mock mode for development
- Real YOLOv8 integration capability
- Configurable label mapping
- Performance metrics

### Frontend

**Technology Stack:**
- Vanilla HTML5
- Vanilla JavaScript (ES6+)
- WebSocket API
- Fetch API

**User Interfaces:**
1. **User Frontend** - Image submission and detection results
2. **Ward Admin Frontend** - Truck management and alert monitoring
3. **Municipality Admin Frontend** - System-wide oversight and analytics

## Data Flow

### Detection Flow

1. User uploads image via frontend
2. Frontend sends POST request to `/api/v1/detect`
3. Backend forwards image to Model Service
4. Model Service processes image with YOLOv8
5. Model Service returns detection results
6. Backend maps labels to categories (degradable/non_degradable)
7. Backend stores detection record in database
8. If confidence > threshold, backend creates alert
9. Backend broadcasts alert via WebSocket
10. Frontend receives real-time update

### Truck Management Flow

1. Ward admin views alerts via frontend
2. Ward admin dispatches truck to alert
3. Backend validates permissions
4. Backend updates truck state in database
5. Backend broadcasts truck update via WebSocket
6. Municipality admin sees update in real-time

## Database Schema

### Core Tables

**Users**
- Authentication and authorization
- Role-based access control
- Ward assignment for ward admins

**Wards** 
- Geographic/administrative divisions
- Municipality hierarchy

**Trucks**
- Fleet management
- State tracking
- Capacity management

**Detection Records**
- Waste detection history
- Image metadata
- Classification results

**Alerts**
- High-confidence detection notifications
- Severity classification
- Acknowledgment tracking

**Truck Tasks**
- Dispatch workflow
- Task state management
- Performance tracking

## Security Architecture

### Authentication
- JWT-based authentication
- Token expiration handling
- Secure password hashing (bcrypt)

### Authorization
- Role-based access control (RBAC)
- Ward-level permissions
- API endpoint protection

### Data Security
- Password hashing
- Secure token generation
- Input validation
- SQL injection prevention (ORM)

## Scalability Considerations

### Current Limitations (MVP)
- Single database instance
- In-memory WebSocket connections
- Synchronous model inference
- No caching layer

### Future Enhancements
- Database replication
- Redis for WebSocket connection management
- Asynchronous task queue for model inference
- CDN for static assets
- Load balancing

## Deployment Architecture

### Development
- Local Python execution
- SQLite database
- Mock model service
- File-based frontend serving

### Production
- Docker containerization
- PostgreSQL database
- Real YOLOv8 model
- Nginx reverse proxy
- Environment-based configuration

## Monitoring and Logging

### Current Implementation
- SQL query logging
- Request/response logging
- Error tracking

### Future Enhancements
- Structured logging
- Performance metrics
- Health check endpoints
- Alert notifications

## API Design Principles

### RESTful Conventions
- Resource-based URLs
- HTTP method semantics
- Standard status codes
- JSON request/response

### WebSocket Design
- Real-time event broadcasting
- Connection management
- Error handling
- Reconnection logic

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock dependencies
- Fast execution

### Integration Tests
- API endpoint testing
- Database operations
- WebSocket communication

### End-to-End Tests
- Complete user flows
- Multi-component interaction
- Real data scenarios

## Performance Considerations

### Current Optimizations
- Async I/O operations
- Database connection pooling
- Efficient model inference

### Bottlenecks
- Model inference latency
- Database query complexity
- WebSocket connection limits

### Optimization Opportunities
- Model quantization
- Database indexing
- Response caching
- CDN deployment
