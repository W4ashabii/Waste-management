# Model Service

YOLOv8 inference microservice for waste detection.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MOCK_MODE="true"  # Set to "false" for real model

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## Adding Real YOLOv8 Model

1. Install ultralytics:
```bash
pip install ultralytics
```

2. Download model:
```bash
# Download YOLOv8n model
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

3. Update `app/main.py`:
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")

# In detect endpoint:
results = model(img)
# Process results...
```

4. Set `MOCK_MODE="false"` in environment

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
