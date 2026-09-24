# Backend Service

FastAPI backend for the Waste Management MVP.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
export MODEL_SERVICE_URL="http://localhost:8001"
export SECRET_KEY="dev-secret-key"

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Database Seeding

```bash
python seed_db.py
```

## Running Tests

```bash
pytest app/tests.py -v
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
