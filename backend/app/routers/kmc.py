"""KMC staff portal: city-wide view of all wards."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_kmc_user
from app.database import get_db
from app.models import Driver, Notification, Program, Report, Route, Update, Vehicle, Ward
from app.routers.ward import VehicleIn
from app.serializers import kmc_program, kmc_report, notification_out, today_short, update_out, vehicle_out, ward_stat
from app.services import KMC_SCOPE, active_route, format_time, get_ward, notify, ward_routes, ward_scope

router = APIRouter(prefix="/api/v1/kmc", tags=["kmc"], dependencies=[Depends(get_kmc_user)])


class CompleteIn(BaseModel):
    kg: int = Field(ge=0)


class AssignmentIn(BaseModel):
    vehicle: str
    driver: str = ""


class ScheduleIn(BaseModel):
    time: str = Field(pattern=r"^\d{1,2}:\d{2}$")
    kind: str


class KmcProgramIn(BaseModel):
    name: str = Field(min_length=1)
    ward: int
    date: str
    time: str
    description: str = ""
    expected: int = Field(default=0, ge=0)


class KmcUpdateIn(BaseModel):
    category: str
    title: str = Field(min_length=1)
    message: str = ""
    audience: str = "All wards"


async def tracked_route(db: AsyncSession, ward_n: int) -> Route:
    route = active_route(await ward_routes(db, ward_n))
    if route is None:
        raise HTTPException(status_code=404, detail=f"Ward {ward_n} has no route with a vehicle")
    return route


@router.get("/state")
async def get_state(db: AsyncSession = Depends(get_db)):
    wards = list((await db.execute(select(Ward).order_by(Ward.n))).scalars())
    routes = list((await db.execute(select(Route).order_by(Route.ward, Route.n))).scalars())
    by_ward: dict[int, list[Route]] = {}
    for r in routes:
        by_ward.setdefault(r.ward, []).append(r)
    kmc_routes = []
    for w in wards:
        if (r := active_route(by_ward.get(w.n, []))) is not None:
            kmc_routes.append({"w": w.n, "n": r.n, "v": r.vehicle})

    vehicles = (await db.execute(select(Vehicle).order_by(Vehicle.id))).scalars()
    programs = (await db.execute(select(Program).order_by(Program.id))).scalars()
    updates = (await db.execute(select(Update).order_by(Update.id.desc()))).scalars()
    reports = (await db.execute(select(Report).order_by(Report.id.desc()))).scalars()
    notifications = (await db.execute(
        select(Notification).where(Notification.scope == KMC_SCOPE).order_by(Notification.id.desc()).limit(30)
    )).scalars()
    drivers = (await db.execute(select(Driver.name).order_by(Driver.id))).scalars()
    return {
        "drivers": list(drivers),
        "wards": [ward_stat(w) for w in wards],
        "wardStatus": {w.n: w.status for w in wards},
        "schedule": {w.n: {"t": w.schedule_time, "k": w.schedule_kind} for w in wards},
        "routes": kmc_routes,
        "vehicles": [vehicle_out(v) for v in vehicles],
        "programs": [kmc_program(p) for p in programs],
        "updates": [update_out(u) for u in updates],
        "reports": [kmc_report(r) for r in reports],
        "notifications": [notification_out(x) for x in notifications],
    }


@router.post("/wards/{ward_n}/complete")
async def complete_ward(ward_n: int, body: CompleteIn, db: AsyncSession = Depends(get_db)):
    ward = await get_ward(db, ward_n)
    route = await tracked_route(db, ward_n)
    route.status, route.kg = "Completed", route.kg + body.kg
    ward.status = "Completed"
    ward.tons += body.kg / 1000
    await db.commit()
    return {**ward_stat(ward), "status": ward.status}


@router.post("/wards/{ward_n}/restart")
async def restart_ward(ward_n: int, db: AsyncSession = Depends(get_db)):
    ward = await get_ward(db, ward_n)
    route = await tracked_route(db, ward_n)
    route.status = "In Progress"
    ward.status = "In Progress"
    await db.commit()
    return {**ward_stat(ward), "status": ward.status}


@router.put("/wards/{ward_n}/assignment")
async def assign_route(ward_n: int, body: AssignmentIn, db: AsyncSession = Depends(get_db)):
    await get_ward(db, ward_n)
    vehicle = await db.get(Vehicle, body.vehicle)
    if vehicle is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {body.vehicle} not found")
    route = await tracked_route(db, ward_n)
    route.vehicle = vehicle.id
    vehicle.ward = ward_n
    if body.driver:
        vehicle.driver = body.driver
    await db.commit()
    return {"w": ward_n, "n": route.n, "v": route.vehicle}


@router.put("/wards/{ward_n}/schedule")
async def change_schedule(ward_n: int, body: ScheduleIn, db: AsyncSession = Depends(get_db)):
    ward = await get_ward(db, ward_n)
    old = ward.schedule_time
    ward.schedule_time, ward.schedule_kind = body.time, body.kind
    if old != body.time:
        for r in await ward_routes(db, ward_n):
            r.time = body.time
        db.add(Update(
            category="Collection", title=f"Collection timing changed for Ward {ward_n}",
            body=f"Previous: {format_time(old)} → New: {format_time(body.time)}", audience=f"Ward {ward_n}", date=today_short(),
        ))
        notify(db, KMC_SCOPE, f"Schedule changed in Ward {ward_n}", "/kmc/updates")
        notify(db, ward_scope(ward_n), "Collection schedule changed by KMC", "/ward/updates")
    await db.commit()
    return {"t": ward.schedule_time, "k": ward.schedule_kind}


@router.post("/vehicles", status_code=status.HTTP_201_CREATED)
async def add_vehicle(body: VehicleIn, db: AsyncSession = Depends(get_db)):
    if await db.get(Vehicle, body.id) is not None:
        raise HTTPException(status_code=409, detail=f"Vehicle {body.id} already exists")
    vehicle = Vehicle(id=body.id, driver=body.drv, capacity=body.cap, status=body.st, note=body.note)
    db.add(vehicle)
    await db.commit()
    return vehicle_out(vehicle)


@router.post("/programs", status_code=status.HTTP_201_CREATED)
async def add_program(body: KmcProgramIn, db: AsyncSession = Depends(get_db)):
    await get_ward(db, body.ward)
    time = format_time(body.time)
    program = Program(
        name=body.name, ward=body.ward, date=body.date, time=time, expected=body.expected,
        status="Upcoming", approval="Approved", description=body.description,
    )
    db.add(program)
    db.add(Update(
        category="Awareness", title=f"{body.name} in Ward {body.ward}",
        body=f"Register through the Citizen app. {body.date}, {time}.", audience=f"Ward {body.ward}", date=today_short(),
    ))
    notify(db, ward_scope(body.ward), f"KMC scheduled \"{body.name}\" in your ward", "/ward/awareness")
    await db.commit()
    return kmc_program(program)


@router.post("/updates", status_code=status.HTTP_201_CREATED)
async def add_update(body: KmcUpdateIn, db: AsyncSession = Depends(get_db)):
    update = Update(category=body.category, title=body.title, body=body.message, audience=body.audience, date=today_short())
    db.add(update)
    await db.commit()
    return update_out(update)
