from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import random
from app.config import settings

app = FastAPI(title="YOLOv8 Model Service")


class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class Prediction(BaseModel):
    label: str
    class_id: int
    confidence: float
    bbox: List[int]


class DetectionResponse(BaseModel):
    predictions: List[Prediction]
    inference_ms: int


# TODO: Replace with actual YOLOv8 model loading
# model = YOLO("yolov8n.pt")


@app.post("/detect", response_model=DetectionResponse)
async def detect(image: UploadFile = File(...)):
    """
    Detect objects in image using YOLOv8 model.
    In mock mode, returns deterministic test outputs.
    """
    if settings.MOCK_MODE:
        # Mock mode for development - return deterministic predictions
        mock_labels = ["plastic_bottle", "food_waste", "paper", "metal_can"]
        selected_label = random.choice(mock_labels)
        
        predictions = [
            {
                "label": selected_label,
                "class_id": mock_labels.index(selected_label),
                "confidence": round(random.uniform(0.75, 0.98), 2),
                "bbox": [random.randint(0, 100), random.randint(0, 100), 
                        random.randint(50, 200), random.randint(50, 200)]
            }
        ]
        
        return {
            "predictions": predictions,
            "inference_ms": random.randint(80, 150)
        }
    else:
        # TODO: Implement actual YOLOv8 inference
        # from PIL import Image
        # img = Image.open(image.file)
        # results = model(img)
        # ... process results ...
        pass


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
