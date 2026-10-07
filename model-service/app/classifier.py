"""Local wrapper around the W4ashabii/waste_classifier YOLOv8s-cls model."""
import io
import threading
import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from pi_heif import register_heif_opener

from app.config import settings

# Phone cameras often upload HEIC/HEIF.
register_heif_opener()

# Model class name -> category used by the backend.
CATEGORIES = {"Bio": "degradable", "Non_Bio": "non_degradable"}


class InvalidImage(ValueError):
    pass


def resolve_weights() -> Path:
    if settings.WEIGHTS_PATH and Path(settings.WEIGHTS_PATH).is_file():
        return Path(settings.WEIGHTS_PATH)
    local = Path(settings.WEIGHTS_DIR) / settings.HF_FILENAME
    if local.is_file():
        return local
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo_id=settings.HF_REPO_ID, filename=settings.HF_FILENAME, local_dir=settings.WEIGHTS_DIR))


class WasteClassifier:
    def __init__(self):
        self._model = None
        self._lock = threading.Lock()
        self.weights: Path | None = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        from ultralytics import YOLO

        self.weights = resolve_weights()
        self._model = YOLO(str(self.weights), task="classify")
        # Warm up so the first request is not slow.
        self._predict(Image.new("RGB", (settings.IMAGE_SIZE, settings.IMAGE_SIZE)))

    def _predict(self, image: Image.Image):
        kwargs = {"imgsz": settings.IMAGE_SIZE, "verbose": False}
        if settings.DEVICE:
            kwargs["device"] = settings.DEVICE
        with self._lock:
            return self._model.predict(image, **kwargs)[0]

    def classify(self, data: bytes) -> dict:
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise InvalidImage("File is not a readable image") from exc
        image = image.convert("RGB")

        start = time.perf_counter()
        result = self._predict(image)
        elapsed = round((time.perf_counter() - start) * 1000)

        probs = result.probs
        names = result.names
        top = int(probs.top1)
        label = names[top]
        return {
            "label": label,
            "category": CATEGORIES.get(label, "non_degradable"),
            "confidence": round(float(probs.top1conf), 4),
            "probabilities": {names[i]: round(float(p), 4) for i, p in enumerate(probs.data.tolist())},
            "inference_ms": elapsed,
        }


classifier = WasteClassifier()
