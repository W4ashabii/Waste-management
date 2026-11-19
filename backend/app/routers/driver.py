"""Driver section: today's routes for the vehicles a driver is assigned to, stop-by-stop
progress, live GPS position and vehicle issue reports. A driver account is linked to
vehicles by name (Vehicle.driver == User.name), which ward staff set in their portal."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.auth import get_driver_user
from app.database import get_db
from app.models import Notification, Report, Route, Stop, User, Vehicle
from app.serializers import location_out, notification_out, route_detail, vehicle_out, ward_report
from app.services import (
    KMC_SCOPE, add_history, get_ward, notify, report_ref, route_stops, today, user_scope, ward_scope,
)

router = APIRouter(prefix="/api/v1/driver", tags=["driver"])

STATUS_ORDER = {"In Progress": 0, "Delayed": 1, "Upcoming": 2, "Incomplete": 3, "Completed": 4}


class LocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)
    heading: float | None = None
    speed: float | None = Field(default=None, ge=0)
    vehicle: str | None = None


class StopIn(BaseModel):
    status: Literal["Pending", "Collected", "Skipped"]


class FinishIn(BaseModel):
    outcome: Literal["completed", "delayed", "incomplete"]
    kg: int = Field(default=0, ge=0, le=50000)


class IssueIn(BaseModel):
    type: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    vehicle: str | None = None


async def my_vehicles(db: AsyncSession, user: User) -> list[Vehicle]:
    return list((await db.execute(select(Vehicle).where(Vehicle.driver == user.name).order_by(Vehicle.id))).scalars())


async def my_routes(db: AsyncSession, vehicle_ids: list[str]) -> list[Route]:
    if not vehicle_ids:
        return []
    routes = list((await db.execute(select(Route).where(Route.vehicle.in_(vehicle_ids)))).scalars())
    return sorted(routes, key=lambda r: (STATUS_ORDER.get(r.status, 9), r.time, r.ward, r.n))


async def my_route(db: AsyncSession, user: User, route_id: int) -> Route:
    route = await db.get(Route, route_id)
    vehicles = {v.id for v in await my_vehicles(db, user)}
    if route is None or route.vehicle not in vehicles:
        raise HTTPException(status_code=404, detail="This route is not assigned to you")
    return route


@router.get("/state")
async def state(user: User = Depends(get_driver_user), db: AsyncSession = Depends(get_db)):
    vehicles = await my_vehicles(db, user)
    routes = await my_routes(db, [v.id for v in vehicles])
    stops = await route_stops(db, [r.id for r in routes])
    issues = (await db.execute(select(Report).where(Report.user_id == user.id).order_by(Report.id.desc()).limit(30))).scalars()
    notifications = (await db.execute(
        select(Notification).where(Notification.scope == user_scope(user.id)).order_by(Notification.id.desc()).limit(30)
    )).scalars()
    return {
        "vehicles": [{**vehicle_out(v), "location": location_out(v)} for v in vehicles],
        "routes": [route_detail(r, stops.get(r.id, [])) for r in routes],
        "issues": [ward_report(r) for r in issues],
        "notifications": [notification_out(x) for x in notifications],
    }


@router.post("/routes/{route_id}/start")
async def start(route_id: int, user: User = Depends(get_driver_user), db: AsyncSession = Depends(get_db)):
    route = await my_route(db, user, route_id)
    if route.status == "Completed":
        raise HTTPException(status_code=400, detail="This route is already completed")
    await services.start_route(db, await get_ward(db, route.ward), route)
    notify(db, ward_scope(route.ward), f"{user.name} started Route {route.n} ({route.area})", "/ward/collection")
    await db.commit()
    return route_detail(route, (await route_stops(db, [route.id])).get(route.id, []))


@router.post("/stops/{stop_id}")
async def set_stop(stop_id: int, body: StopIn, user: User = Depends(get_driver_user), db: AsyncSession = Depends(get_db)):
    stop = await db.get(Stop, stop_id)
    if stop is None:
        raise HTTPException(status_code=404, detail="Stop not found")
    route = await my_route(db, user, stop.route_id)
    if route.status not in ("In Progress", "Delayed"):
        raise HTTPException(status_code=400, detail="Start the route first")
    stop.status = body.status
    stop.collected_at = datetime.utcnow() if body.status != "Pending" else None
    await db.commit()
    return route_detail(route, (await route_stops(db, [route.id])).get(route.id, []))


@router.post("/routes/{route_id}/finish")
async def finish(route_id: int, body: FinishIn, user: User = Depends(get_driver_user), db: AsyncSession = Depends(get_db)):
    route = await my_route(db, user, route_id)
    if body.outcome == "completed" and body.kg <= 0:
        raise HTTPException(status_code=422, detail="Enter the weight collected (kg)")
    await services.apply_driver_update(db, await get_ward(db, route.ward), route, body.outcome, body.kg)
    await db.commit()
    return route_detail(route, (await route_stops(db, [route.id])).get(route.id, []))


@router.post("/location")
async def location(body: LocationIn, user: User = Depends(get_driver_user), db: AsyncSession = Depends(get_db)):
    """The driver section sends a GPS fix every few seconds while a route is open. It moves the
    chosen vehicle, else the vehicle of the route in progress, else the driver's first vehicle."""
    vehicles = await my_vehicles(db, user)
    if not vehicles:
        raise HTTPException(status_code=400, detail="No vehicle is assigned to you")
    vehicle = next((v for v in vehicles if v.id == body.vehicle), None)
    if vehicle is None:
        active = next((r for r in await my_routes(db, [v.id for v in vehicles]) if r.status == "In Progress"), None)
        vehicle = next((v for v in vehicles if active and v.id == active.vehicle), vehicles[0])
    vehicle.lat, vehicle.lng = body.lat, body.lng
    vehicle.accuracy, vehicle.heading, vehicle.speed = body.accuracy, body.heading, body.speed
    vehicle.located_at = datetime.utcnow()
    await db.commit()
    return {"vehicle": vehicle.id, "location": location_out(vehicle)}


@router.post("/issues", status_code=status.HTTP_201_CREATED)
async def report_issue(body: IssueIn, user: User = Depends(get_driver_user), db: AsyncSession = Depends(get_db)):
    vehicles = await my_vehicles(db, user)
    vehicle = next((v for v in vehicles if v.id == body.vehicle), vehicles[0] if vehicles else None)
    if vehicle is None:
        raise HTTPException(status_code=400, detail="No vehicle is assigned to you")
    routes = await my_routes(db, [vehicle.id])
    ward = vehicle.ward or (routes[0].ward if routes else None)
    if ward is None:
        raise HTTPException(status_code=400, detail="Your vehicle has no ward; contact KMC")
    report = Report(
        type=body.type.strip(), ward=ward, source="Driver", date=today(), status="Pending",
        route=routes[0].n if routes and routes[0].ward == ward else None,
        description=f"{vehicle.id}: {body.description.strip()}".rstrip(": "), category="Vehicle", location="", notes=[],
        user_id=user.id,
    )
    add_history(report, "Pending", f"Reported by {user.name}")
    db.add(report)
    await db.flush()
    notify(db, ward_scope(ward), f"{user.name} reported a vehicle issue on {vehicle.id} ({report_ref(report.id)})", "/ward/reports")
    notify(db, KMC_SCOPE, f"Vehicle issue on {vehicle.id} in Ward {ward}", "/kmc/collection")
    await db.commit()
    return ward_report(report)
