from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.classifier import InvalidImage, classifier
from app.config import settings


class ClassifyResponse(BaseModel):
    label: str
    category: str
    confidence: float
    probabilities: dict[str, float]
    inference_ms: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_in_threadpool(classifier.load)
    yield


app = FastAPI(title="Waste Classifier Service", lifespan=lifespan)


@app.post("/classify", response_model=ClassifyResponse)
async def classify(image: UploadFile = File(...)):
    data = await image.read(settings.MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")
    try:
        return await run_in_threadpool(classifier.classify, data)
    except InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/health")
async def health():
    return {
        "status": "healthy" if classifier.loaded else "loading",
        "model": settings.HF_REPO_ID,
        "weights": str(classifier.weights) if classifier.weights else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
