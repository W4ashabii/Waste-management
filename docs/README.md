# Documentation

This directory contains comprehensive documentation for the Waste Management System.

## Documentation Files

### Architecture
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, component design, and technical decisions

### API Documentation
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference with endpoints, request/response formats, and examples

### Development Guidelines
- **[GUARDRAILS.md](GUARDRAILS.md)** - Coding standards, best practices, and development guidelines

### Testing
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing guide including setup, execution, and best practices

## Quick Reference

### System Overview
- **Backend**: FastAPI with PostgreSQL/SQLite
- **Model Service**: YOLOv8 inference (mock mode available)
- **Frontend**: Vanilla HTML/JS with WebSocket support
- **Authentication**: JWT-based with role-based access control

### Key Components
- User authentication and authorization
- Waste detection with YOLOv8
- Real-time alerts via WebSocket
- Truck management and dispatching
- Ward-level analytics

### User Roles
- **User**: Submit images, view detections
- **Ward Admin**: Manage trucks, handle alerts
- **Municipality Admin**: System oversight, analytics

## API Endpoints Summary

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration

### Detection
- `POST /api/v1/detect` - Submit image for waste detection

### Trucks
- `GET /api/v1/trucks` - List trucks
- `POST /api/v1/trucks/{id}/dispatch` - Dispatch truck
- `POST /api/v1/trucks/{id}/update_state` - Update truck state

### Alerts
- `GET /api/v1/alerts` - Get alerts (filtered by ward)

### Analytics
- `GET /api/v1/analytics/ward/{id}` - Get ward analytics

### WebSocket
- `WS /ws/alerts` - Real-time alert and truck updates

## Development Workflow

### Setting Up
1. Clone repository
2. Install dependencies
3. Run `./run_local.sh` for local development
4. Seed database with test data

### Code Quality
- Follow guidelines in [GUARDRAILS.md](GUARDRAILS.md)
- Write tests as per [TESTING_GUIDE.md](TESTING_GUIDE.md)
- Ensure code follows architecture in [ARCHITECTURE.md](ARCHITECTURE.md)

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### API Testing
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Login
curl -X POST -F "username=user@example.com" -F "password=user123" \
  http://localhost:8000/api/v1/auth/login

# Detection
curl -X POST -F "image=@test.jpg" \
  http://localhost:8000/api/v1/detect
```

## Documentation Standards

### Code Documentation
- All functions must have docstrings
- Use type hints for all functions
- Add comments for complex logic
- Provide usage examples

### API Documentation
- Use OpenAPI/Swagger for interactive docs
- Include request/response examples
- Document all error codes
- Specify authentication requirements

### Architecture Documentation
- Include architecture diagrams
- Document design decisions
- Explain component interactions
- Provide rationale for choices

## Keeping Documentation Updated

### When to Update
- Code changes that affect API contracts
- Architecture changes or new components
- New features or functionality
- Breaking changes or deprecations

### Review Process
- Documentation should be reviewed alongside code
- Ensure examples are accurate
- Verify all links and references
- Update diagrams as needed

## Resources

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

### Internal Resources
- Project README (root directory)
- Test documentation (tests/README.md)
- Component README files (backend/, model-service/)

## Contributing to Documentation

### Guidelines
- Use clear, concise language
- Include code examples where helpful
- Maintain consistent formatting
- Update table of contents when adding sections

### Format
- Use Markdown for all documentation
- Include code blocks with syntax highlighting
- Use proper heading hierarchy
- Add relevant diagrams and images

## Support

For questions about documentation:
- Check existing documentation first
- Review code examples and tests
- Consult API documentation for endpoint details
- Refer to testing guide for test-related questions

## Version Control

Documentation is version-controlled with the codebase. Always update documentation when making changes to:
- API endpoints
- Database schema
- Authentication/authorization
- Architecture and design
- Configuration and deployment
