"""Domain helpers shared by the routers."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import sms
from app.models import Notification, Report, Route, Stop, Ward

KMC_SCOPE = "kmc"


def ward_scope(n: int) -> str:
    return f"ward:{n}"


def user_scope(user_id: int) -> str:
    return f"user:{user_id}"


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def report_ref(report_id: int) -> str:
    """Reference number shown to citizens, e.g. WR-00125."""
    return f"WR-{report_id:05d}"


def add_history(report: Report, status: str, note: str | None = None) -> None:
    report.history = [*(report.history or []), {"status": status, "at": iso(datetime.utcnow()), "note": note or None}]


def notify(db: AsyncSession, scope: str, text: str, href: str) -> None:
    db.add(Notification(scope=scope, text=text, href=href))


def format_time(value: str) -> str:
    """"13:05" -> "1:05 PM" (same as src/lib/format.ts)."""
    try:
        h, m = (int(x) for x in value.split(":"))
    except ValueError:
        return value
    return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


async def get_ward(db: AsyncSession, n: int) -> Ward:
    ward = await db.get(Ward, n)
    if ward is None:
        raise HTTPException(status_code=404, detail=f"Ward {n} not found")
    return ward


async def ward_routes(db: AsyncSession, n: int) -> list[Route]:
    result = await db.execute(select(Route).where(Route.ward == n).order_by(Route.n))
    return list(result.scalars())


async def get_route(db: AsyncSession, ward: int, n: int) -> Route:
    result = await db.execute(select(Route).where(Route.ward == ward, Route.n == n))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route {n} not found in Ward {ward}")
    return route


def active_route(routes: list[Route]) -> Route | None:
    """The route KMC tracks for a ward: the first unfinished one with a vehicle,
    otherwise the last route with a vehicle."""
    with_vehicle = [r for r in routes if r.vehicle]
    for r in with_vehicle:
        if r.status != "Completed":
            return r
    return with_vehicle[-1] if with_vehicle else None


def ward_status_from_routes(routes: list[Route], current: str) -> str:
    statuses = {r.status for r in routes}
    if not statuses:
        return current
    if "Incomplete" in statuses:
        return "Incomplete"
    if "Delayed" in statuses:
        return "Delayed"
    if statuses == {"Completed"}:
        return "Completed"
    return "In Progress"


async def refresh_ward_status(db: AsyncSession, ward: Ward) -> None:
    ward.status = ward_status_from_routes(await ward_routes(db, ward.n), ward.status)


async def route_stops(db: AsyncSession, route_ids: list[int]) -> dict[int, list[Stop]]:
    if not route_ids:
        return {}
    result = await db.execute(select(Stop).where(Stop.route_id.in_(route_ids)).order_by(Stop.route_id, Stop.seq))
    by_route: dict[int, list[Stop]] = {}
    for stop in result.scalars():
        by_route.setdefault(stop.route_id, []).append(stop)
    return by_route


async def start_route(db: AsyncSession, ward: Ward, route: Route) -> None:
    route.status = "In Progress"
    route.started_at = route.started_at or datetime.utcnow()
    route.completed_at = None
    await refresh_ward_status(db, ward)


async def apply_driver_update(db: AsyncSession, ward: Ward, route: Route, outcome: str, kg: int) -> None:
    """A driver's end-of-route report: completed (with the weight), delayed or incomplete.
    Used by the ward portal (on the driver's behalf) and by the driver app. The caller commits."""
    if outcome == "completed":
        ward.tons = max(0.0, ward.tons + (kg - route.kg) / 1000)
        route.status, route.kg, route.completed_at = "Completed", kg, datetime.utcnow()
        for stop in (await route_stops(db, [route.id])).get(route.id, []):
            if stop.status == "Pending":
                stop.status, stop.collected_at = "Collected", datetime.utcnow()
    elif outcome == "delayed":
        route.status = "Delayed"
        report = Report(
            type="Vehicle breakdown", ward=ward.n, source="Driver", date=today(), status="Pending", route=route.n,
            description=f"{route.vehicle} has a problem; Route {route.n} is delayed.", category="Vehicle", location=route.area,
            notes=[],
        )
        add_history(report, "Pending", "Reported by the driver")
        db.add(report)
        notify(db, ward_scope(ward.n), f"Route {route.n} delayed: driver reported a vehicle problem", "/ward/reports")
        notify(db, KMC_SCOPE, f"Collection delayed in Ward {ward.n} (Route {route.n})", "/kmc/collection")
        await sms.alert_ward(
            db, ward.n, f"Collection on Route {route.n} ({route.area}) is delayed today by a vehicle problem. "
            "We will update you when it resumes.", "delay",
        )
    else:
        route.status = "Incomplete"
        notify(db, KMC_SCOPE, f"Route {route.n} incomplete in Ward {ward.n}", "/kmc/collection")
    await refresh_ward_status(db, ward)


def today() -> str:
    now = datetime.now()
    return f"{now:%b} {now.day}"
