"""Domain helpers shared by the ward and KMC routers."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, Route, Ward

KMC_SCOPE = "kmc"


def ward_scope(n: int) -> str:
    return f"ward:{n}"


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
