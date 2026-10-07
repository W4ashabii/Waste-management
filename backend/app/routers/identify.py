"""Waste identification: photos are classified by the local model service
(W4ashabii/waste_classifier, YOLOv8s-cls: Bio vs Non_Bio)."""
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_optional_user, require_ward_access
from app.config import settings
from app.database import get_db
from app.models import Identification, Portal, User, Ward
from app.serializers import identification_out

router = APIRouter(prefix="/api/v1", tags=["identify"])


async def classify(data: bytes, filename: str, content_type: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=settings.MODEL_SERVICE_TIMEOUT) as client:
            response = await client.post(f"{settings.MODEL_SERVICE_URL}/classify", files={"image": (filename, data, content_type)})
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Waste classifier is not available")
    if response.status_code in (400, 413):
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail", "Invalid image"))
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Waste classifier failed")
    return response.json()


@router.post("/identify", status_code=status.HTTP_201_CREATED)
async def identify(
    image: UploadFile = File(...),
    ward: int | None = Form(default=None),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Classify a waste photo. Login is optional (citizens/cameras may post anonymously);
    ward staff default to their own ward."""
    if user is not None and user.portal == Portal.WARD:
        ward = ward if ward is not None else user.ward
        if ward is not None:
            require_ward_access(user, ward)
    if ward is not None and await db.get(Ward, ward) is None:
        raise HTTPException(status_code=404, detail=f"Ward {ward} not found")

    data = await image.read(settings.MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")

    result = await classify(data, image.filename or "upload", image.content_type or "application/octet-stream")
    record = Identification(
        ward=ward, user_id=user.id if user else None, label=result["label"], category=result["category"],
        confidence=result["confidence"], probabilities=result["probabilities"], filename=image.filename,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {**identification_out(record), "inference_ms": result.get("inference_ms")}


@router.get("/identifications")
async def list_identifications(
    ward: int | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.portal == Portal.WARD:
        ward = ward if ward is not None else user.ward
        if ward is None:
            raise HTTPException(status_code=400, detail="Select a ward first")
        require_ward_access(user, ward)
    where = [Identification.ward == ward] if ward is not None else []

    items = (await db.execute(select(Identification).where(*where).order_by(Identification.id.desc()).limit(limit))).scalars()
    counts = dict((await db.execute(
        select(Identification.category, func.count()).where(*where).group_by(Identification.category)
    )).all())
    degradable, non_degradable = counts.get("degradable", 0), counts.get("non_degradable", 0)
    return {
        "items": [identification_out(i) for i in items],
        "summary": {"total": degradable + non_degradable, "degradable": degradable, "non_degradable": non_degradable},
    }
