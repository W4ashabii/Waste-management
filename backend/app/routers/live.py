"""Live collection map: routes, stops and the GPS position each driver last sent.
Shared by the KMC and ward portals and the citizen section."""
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_ward_access
from app.config import settings
from app.database import get_db
from app.geo import WARD_CENTRES
from app.models import Portal, Route, User, Vehicle
from app.serializers import location_out, route_detail, vehicle_out
from app.services import get_ward, iso, route_stops

router = APIRouter(prefix="/api/v1", tags=["live"])
UPLOAD_NAME = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp|heic)$")


async def live_data(db: AsyncSession, ward: int | None) -> dict:
    query = select(Route).where(Route.vehicle != "").order_by(Route.ward, Route.n)
    if ward is not None:
        query = query.where(Route.ward == ward)
    routes = list((await db.execute(query)).scalars())
    stops = await route_stops(db, [r.id for r in routes])
    vehicle_ids = {r.vehicle for r in routes}
    vehicles = list((await db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids)).order_by(Vehicle.id))).scalars()) if vehicle_ids else []
    return {
        "now": iso(datetime.utcnow()),
        "liveSeconds": settings.LIVE_LOCATION_SECONDS,
        "centres": {n: c for n, c in WARD_CENTRES.items() if ward is None or n == ward},
        "routes": [route_detail(r, stops.get(r.id, [])) for r in routes],
        "vehicles": [{**vehicle_out(v), "location": location_out(v)} for v in vehicles],
    }


@router.get("/live")
async def live(ward: int | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Staff see their ward (ward staff) or any/all wards (KMC); citizens see their own ward."""
    if user.portal == Portal.WARD:
        ward = ward if ward is not None else user.ward
        if ward is None:
            raise HTTPException(status_code=400, detail="Select a ward first")
        require_ward_access(user, ward)
    elif user.portal == Portal.CITIZEN:
        ward = user.ward
    elif user.portal == Portal.DRIVER and ward is None:
        raise HTTPException(status_code=400, detail="Choose a ward")
    if ward is not None:
        await get_ward(db, ward)
    return await live_data(db, ward)


@router.get("/uploads/{name}")
async def upload(name: str):
    """Report photos. Names are random, so a link is only known to people who can see the report."""
    if not UPLOAD_NAME.match(name):
        raise HTTPException(status_code=404, detail="Not found")
    path = Path(settings.UPLOAD_DIR) / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)
