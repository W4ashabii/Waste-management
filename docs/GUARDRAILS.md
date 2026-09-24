# Waste Management System - Code Guardrails

## Purpose

This document establishes coding standards, architectural principles, and development guidelines to ensure code quality, consistency, and maintainability across the Waste Management System codebase.

## Python Code Standards

### Code Style
- **PEP 8 Compliance**: All Python code must follow PEP 8 guidelines
- **Line Length**: Maximum 100 characters per line
- **Imports**: Organize imports in three groups: standard library, third-party, local
- **Naming Conventions**:
  - Variables/Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private members: `_leading_underscore`

### Type Hints
- **Required**: All functions must have type hints
- **Complex Types**: Use `typing` module for complex types
- **Return Types**: Always specify return types
- **Optional Types**: Use `Optional[T]` for nullable values

```python
# Good
async def get_user(user_id: int) -> Optional[User]:
    return await db.execute(select(User).where(User.id == user_id))

# Bad
async def get_user(user_id):
    return await db.execute(select(User).where(User.id == user_id))
```

### Error Handling
- **Specific Exceptions**: Catch specific exceptions, not bare `except:`
- **Resource Cleanup**: Use context managers for resources
- **Logging**: Log errors with appropriate context
- **User Messages**: Never expose internal errors to users

```python
# Good
try:
    user = await get_user(user_id)
except UserNotFoundError as e:
    logger.error(f"User not found: {user_id}")
    raise HTTPException(status_code=404, detail="User not found")

# Bad
try:
    user = await get_user(user_id)
except:
    return "Error occurred"
```

### Async/Await
- **Async Functions**: Use `async/await` for I/O operations
- **Database Operations**: All database operations must be async
- **Blocking Calls**: Avoid blocking calls in async functions
- **Concurrency**: Use proper async patterns for concurrent operations

## API Design Standards

### RESTful Principles
- **Resource-Based URLs**: Use nouns, not verbs
- **HTTP Methods**: Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- **Status Codes**: Use correct HTTP status codes
- **Versioning**: Include API version in URL path

### Endpoint Structure
```python
# Good
@app.get("/api/v1/trucks/{truck_id}")
async def get_truck(truck_id: int):
    return truck

# Bad
@app.get("/getTruck")
async def get_truck():
    return truck
```

### Response Format
- **Consistent Structure**: Use consistent response structures
- **Error Responses**: Include error details in error responses
- **Success Responses**: Include relevant data in success responses
- **HTTP Status**: Use appropriate status codes

### Input Validation
- **Pydantic Models**: Use Pydantic for request validation
- **Required Fields**: Mark required fields clearly
- **Type Validation**: Enforce type constraints
- **Custom Validators**: Add custom validators for business logic

## Database Standards

### Query Patterns
- **ORM Usage**: Use SQLAlchemy ORM, not raw SQL
- **Query Optimization**: Use indexes for frequently queried fields
- **N+1 Problem**: Avoid N+1 query problems
- **Relationship Loading**: Use appropriate relationship loading strategies

### Transaction Management
- **Atomic Operations**: Use transactions for multi-step operations
- **Error Handling**: Rollback on errors
- **Connection Management**: Use context managers for connections
- **Connection Pooling**: Configure appropriate connection pool size

### Schema Design
- **Normalization**: Follow database normalization principles
- **Indexes**: Add indexes for frequently queried columns
- **Foreign Keys**: Use foreign keys for relationships
- **Constraints**: Use database constraints for data integrity

## Security Standards

### Authentication
- **JWT**: Use JWT for authentication
- **Token Expiration**: Set appropriate token expiration
- **Secure Storage**: Never store secrets in code
- **Password Hashing**: Use bcrypt for password hashing

### Authorization
- **Role-Based**: Use role-based access control
- **Least Privilege**: Apply principle of least privilege
- **Resource-Level**: Implement resource-level permissions
- **Audit Logging**: Log authorization decisions

### Data Protection
- **Input Validation**: Validate all user inputs
- **SQL Injection**: Use parameterized queries (ORM)
- **XSS Prevention**: Escape user-generated content
- **CSRF Protection**: Implement CSRF protection for state-changing operations

## Testing Standards

### Test Structure
- **Unit Tests**: Test individual functions/classes
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete user flows
- **Test Organization**: Organize tests by feature/module

### Test Quality
- **Descriptive Names**: Use descriptive test names
- **Independence**: Tests should be independent
- **Repeatability**: Tests should be repeatable
- **Fast Execution**: Tests should run quickly

### Coverage Goals
- **Critical Paths**: 100% coverage for critical paths
- **Business Logic**: 90%+ coverage for business logic
- **API Endpoints**: 80%+ coverage for API endpoints
- **Overall**: Aim for 70%+ overall coverage

### Test Data
- **Fixtures**: Use fixtures for test data
- **Cleanup**: Clean up test data after tests
- **Isolation**: Use test database, not production
- **Realistic**: Use realistic test data

## Documentation Standards

### Code Documentation
- **Docstrings**: All functions must have docstrings
- **Comments**: Add comments for complex logic
- **Type Hints**: Use type hints for clarity
- **Examples**: Provide usage examples in docstrings

### API Documentation
- **OpenAPI**: Use OpenAPI/Swagger for API documentation
- **Examples**: Include request/response examples
- **Error Codes**: Document all possible error codes
- **Authentication**: Document authentication requirements

### Architecture Documentation
- **Diagrams**: Include architecture diagrams
- **Decisions**: Document architectural decisions
- **Patterns**: Document design patterns used
- **Rationale**: Explain why certain decisions were made

## Performance Standards

### Response Time
- **API Endpoints**: < 200ms for simple queries
- **Complex Queries**: < 500ms for complex queries
- **Model Inference**: < 1s for model inference
- **WebSocket**: < 100ms message latency

### Resource Usage
- **Memory**: Monitor memory usage, set limits
- **Database**: Optimize database queries
- **Connections**: Use connection pooling
- **Caching**: Implement caching where appropriate

### Scalability
- **Horizontal Scaling**: Design for horizontal scaling
- **Load Balancing**: Consider load balancing strategies
- **Database**: Plan for database scaling
- **Caching**: Use caching for frequently accessed data

## Deployment Standards

### Environment Configuration
- **Environment Variables**: Use environment variables for configuration
- **Secrets Management**: Use secret management for sensitive data
- **Configuration Files**: Separate configuration by environment
- **Validation**: Validate configuration on startup

### Containerization
- **Docker**: Use Docker for containerization
- **Multi-stage Builds**: Use multi-stage builds for smaller images
- **Security Scanning**: Scan images for vulnerabilities
- **Resource Limits**: Set resource limits for containers

### CI/CD
- **Automated Testing**: Run tests automatically on commit
- **Code Quality**: Run code quality checks
- **Security Scanning**: Run security scans
- **Deployment**: Automate deployment process

## Code Review Standards

### Review Process
- **Peer Review**: All code must be peer-reviewed
- **Automated Checks**: Pass automated checks before review
- **Documentation**: Update documentation with code changes
- **Testing**: Include tests with code changes

### Review Criteria
- **Functionality**: Does the code work as intended?
- **Style**: Does the code follow style guidelines?
- **Performance**: Is the code performant?
- **Security**: Is the code secure?
- **Maintainability**: Is the code maintainable?

## Monitoring and Logging Standards

### Logging
- **Structured Logging**: Use structured logging
- **Log Levels**: Use appropriate log levels
- **Context**: Include context in log messages
- **PII**: Never log personally identifiable information

### Monitoring
- **Health Checks**: Implement health check endpoints
- **Metrics**: Collect relevant metrics
- **Alerting**: Set up appropriate alerts
- **Dashboards**: Create monitoring dashboards

## Technology Stack Standards

### Backend
- **Python Version**: Use Python 3.11+
- **Framework**: Use FastAPI for web framework
- **Database**: Use PostgreSQL for production, SQLite for development
- **ORM**: Use SQLAlchemy with async support

### Frontend
- **JavaScript**: Use modern JavaScript (ES6+)
- **Build Tools**: Use appropriate build tools
- **Testing**: Use Jest for frontend testing
- **Linting**: Use ESLint for JavaScript linting

### DevOps
- **Version Control**: Use Git with appropriate branching strategy
- **Containerization**: Use Docker for containerization
- **CI/CD**: Use GitHub Actions or similar
- **Infrastructure**: Use infrastructure as code

## Compliance and Standards

### Legal Compliance
- **GDPR**: Comply with GDPR if handling EU data
- **Data Retention**: Implement appropriate data retention policies
- **User Consent**: Obtain user consent for data collection
- **Data Rights**: Respect user data rights

### Industry Standards
- **OWASP**: Follow OWASP security guidelines
- **Accessibility**: Follow WCAG accessibility guidelines
- **Performance**: Follow web performance best practices
- **SEO**: Follow SEO best practices for public-facing content

## Enforcement

### Automated Checks
- **Linting**: Use automated linting tools
- **Type Checking**: Use type checking tools
- **Security Scanning**: Use automated security scanning
- **Testing**: Require tests to pass

### Manual Review
- **Code Review**: Manual code review process
- **Architecture Review**: Review architectural changes
- **Security Review**: Review security-sensitive changes
- **Performance Review**: Review performance-critical changes

### Continuous Improvement
- **Regular Updates**: Update standards regularly
- **Feedback**: Collect feedback from team
- **Training**: Provide training on standards
- **Metrics**: Track compliance metrics

## Exceptions

### Process for Exceptions
- **Document**: Document reasons for exceptions
- **Approve**: Get approval for exceptions
- **Time-Bound**: Make exceptions time-bound
- **Review**: Review exceptions regularly

### Valid Exception Reasons
- **Emergency**: Emergency fixes
- **Legacy Code**: Temporary exceptions for legacy code
- **Migration**: Migration periods
- **External Requirements**: External requirements that conflict

## References

### External Standards
- [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [REST API Design](https://restfulapi.net/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)

### Internal Resources
- Architecture Documentation
- API Documentation
- Development Guidelines
- Onboarding Materials
