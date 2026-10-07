"""Ward staff portal: one ward's routes, vehicles, programs, updates and reports."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_ward_access
from app.database import get_db
from app.models import Driver, Notification, Program, Report, Update, User, Vehicle
from app.serializers import (
    notification_out, today_short, update_out, vehicle_out, ward_program, ward_report, ward_route, ward_stat,
)
from app.services import (
    KMC_SCOPE, format_time, get_route, get_ward, notify, refresh_ward_status, ward_routes, ward_scope,
)

router = APIRouter(prefix="/api/v1/wards/{ward_n}", tags=["ward"])


async def ward_access(ward_n: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> int:
    require_ward_access(user, ward_n)
    await get_ward(db, ward_n)
    return ward_n


class DriverUpdate(BaseModel):
    outcome: Literal["completed", "delayed", "incomplete"]
    kg: int = Field(default=0, ge=0)


class RoutePatch(BaseModel):
    vehicle: str | None = None
    time: str | None = Field(default=None, pattern=r"^\d{1,2}:\d{2}$")


class VehicleIn(BaseModel):
    id: str = Field(min_length=1, max_length=20)
    drv: str = ""
    cap: int = Field(default=5, ge=0)
    st: str = "Active"
    note: str = ""


class WardProgramIn(BaseModel):
    name: str = Field(min_length=1)
    date: str
    time: str
    location: str = ""
    description: str = ""
    expected: int = Field(default=0, ge=0)
    needsCoordination: bool = False


class UpdateIn(BaseModel):
    category: str
    title: str = Field(min_length=1)
    message: str = ""


class ReportIn(BaseModel):
    type: str = Field(min_length=1)
    source: str = "Citizen"
    route: int | None = None
    description: str = ""
    category: str = "Other"
    location: str = ""


async def ward_state(db: AsyncSession, n: int) -> dict:
    ward = await get_ward(db, n)
    routes = await ward_routes(db, n)
    audience = (f"Ward {n}", "All wards")
    vehicles = (await db.execute(select(Vehicle).where(Vehicle.ward == n).order_by(Vehicle.id))).scalars()
    programs = (await db.execute(select(Program).where(Program.ward == n).order_by(Program.id))).scalars()
    updates = (await db.execute(select(Update).where(Update.audience.in_(audience)).order_by(Update.id.desc()))).scalars()
    reports = (await db.execute(select(Report).where(Report.ward == n).order_by(Report.id.desc()))).scalars()
    notifications = (await db.execute(
        select(Notification).where(Notification.scope == ward_scope(n)).order_by(Notification.id.desc()).limit(30)
    )).scalars()
    drivers = (await db.execute(select(Driver.name).order_by(Driver.id))).scalars()
    return {
        "ward": {**ward_stat(ward), "status": ward.status},
        "drivers": list(drivers),
        "vehicles": [vehicle_out(v) for v in vehicles],
        "routes": [ward_route(r) for r in routes],
        "schedule": {r.n: r.time for r in routes},
        "programs": [ward_program(p) for p in programs],
        "updates": [update_out(u) for u in updates],
        "reports": [ward_report(r) for r in reports],
        "notifications": [notification_out(x) for x in notifications],
    }


@router.get("/state")
async def get_state(ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    return await ward_state(db, ward_n)


@router.post("/routes/{route_n}/start")
async def start_route(route_n: int, ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    route = await get_route(db, ward_n, route_n)
    route.status = "In Progress"
    await refresh_ward_status(db, await get_ward(db, ward_n))
    await db.commit()
    return ward_route(route)


@router.post("/routes/{route_n}/driver-update")
async def driver_update(route_n: int, body: DriverUpdate, ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    ward = await get_ward(db, ward_n)
    route = await get_route(db, ward_n, route_n)
    if body.outcome == "completed":
        ward.tons = max(0.0, ward.tons + (body.kg - route.kg) / 1000)
        route.status, route.kg = "Completed", body.kg
    elif body.outcome == "delayed":
        route.status = "Delayed"
        db.add(Report(
            type="Vehicle breakdown", ward=ward_n, source="Driver", date=today_short(), status="Pending", route=route_n,
            description=f"{route.vehicle} has a problem; Route {route_n} is delayed.", category="Vehicle", location=route.area,
            notes=[],
        ))
        notify(db, ward_scope(ward_n), f"Route {route_n} delayed: driver reported a vehicle problem", "/ward/reports")
        notify(db, KMC_SCOPE, f"Collection delayed in Ward {ward_n} (Route {route_n})", "/kmc/collection")
    else:
        route.status = "Incomplete"
        notify(db, KMC_SCOPE, f"Route {route_n} incomplete in Ward {ward_n}", "/kmc/collection")
    await refresh_ward_status(db, ward)
    await db.commit()
    return ward_route(route)


@router.patch("/routes/{route_n}")
async def patch_route(route_n: int, body: RoutePatch, ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    route = await get_route(db, ward_n, route_n)
    if body.vehicle is not None:
        if body.vehicle and await db.get(Vehicle, body.vehicle) is None:
            raise HTTPException(status_code=404, detail=f"Vehicle {body.vehicle} not found")
        route.vehicle = body.vehicle
    if body.time is not None and body.time != route.time:
        old, route.time = route.time, body.time
        db.add(Update(
            category="Collection", title=f"Collection timing changed for Route {route_n}",
            body=f"Previous: {format_time(old)} → New: {format_time(body.time)}", audience=f"Ward {ward_n}", date=today_short(),
        ))
        notify(db, ward_scope(ward_n), f"Collection schedule changed for Route {route_n}", "/ward/updates")
        notify(db, KMC_SCOPE, f"Collection schedule changed in Ward {ward_n}", "/kmc/updates")
    await db.commit()
    return ward_route(route)


@router.post("/vehicles", status_code=status.HTTP_201_CREATED)
async def add_vehicle(body: VehicleIn, ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    if await db.get(Vehicle, body.id) is not None:
        raise HTTPException(status_code=409, detail=f"Vehicle {body.id} already exists")
    vehicle = Vehicle(id=body.id, driver=body.drv, capacity=body.cap, status=body.st, note=body.note, ward=ward_n)
    db.add(vehicle)
    await db.commit()
    return vehicle_out(vehicle)


@router.post("/programs", status_code=status.HTTP_201_CREATED)
async def create_program(body: WardProgramIn, ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    program = Program(
        name=body.name, ward=ward_n, date=body.date, time=format_time(body.time), location=body.location,
        expected=body.expected, status="Upcoming", approval="Pending KMC review" if body.needsCoordination else "Approved",
        description=body.description,
    )
    db.add(program)
    if body.needsCoordination:
        notify(db, KMC_SCOPE, f"Ward {ward_n} requests review of \"{body.name}\"", "/kmc/awareness")
    else:
        announce_program(db, program)
    await db.commit()
    return ward_program(program)


def announce_program(db: AsyncSession, p: Program) -> None:
    db.add(Update(
        category="Awareness", title=f"{p.name} in Ward {p.ward}",
        body=f"{p.date}, {p.time} at {p.location}. Register in the Citizen app.", audience=f"Ward {p.ward}", date=today_short(),
    ))


@router.post("/updates", status_code=status.HTTP_201_CREATED)
async def add_update(body: UpdateIn, ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    update = Update(category=body.category, title=body.title, body=body.message, audience=f"Ward {ward_n}", date=today_short())
    db.add(update)
    await db.commit()
    return update_out(update)


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def add_report(body: ReportIn, ward_n: int = Depends(ward_access), db: AsyncSession = Depends(get_db)):
    report = Report(
        type=body.type, ward=ward_n, source=body.source, date=today_short(), status="Pending", route=body.route,
        description=body.description, category=body.category, location=body.location, notes=[],
    )
    db.add(report)
    notify(db, ward_scope(ward_n), "New citizen complaint received" if body.source == "Citizen" else f"New report: {body.type}", "/ward/reports")
    await db.commit()
    return ward_report(report)
