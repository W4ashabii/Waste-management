"""Seed the database with the demo data the frontend used to ship as static JSON.

The KMC and ward portals had separate mock datasets. Here they are merged into one
city-wide dataset: KMC data covers every ward, and the ward portal's detailed data
(routes, vehicles, programs, reports) belongs to its demo ward (Ward 17).
"""
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.geo import DEMO_ROUTES, generated_stops
from app.models import Driver, Notification, Portal, Program, Report, Route, Stop, Subscriber, Update, User, Vehicle, Ward
from app.services import KMC_SCOPE, ward_scope

DATA = Path(__file__).parent / "seed_data"
TO_CANONICAL_PROGRAM_STATUS = {"Scheduled": "Upcoming", "Ongoing": "Running"}


def load(name: str):
    with open(DATA / f"{name}.json") as f:
        return json.load(f)


def short_date_key(d: str) -> tuple[int, int]:
    """Sort key for "Oct 5" / "Oct 5, 2026"."""
    try:
        parsed = datetime.strptime(d.split(",")[0], "%b %d")
        return parsed.month, parsed.day
    except ValueError:
        return 0, 0


async def seed(db: AsyncSession) -> bool:
    """Insert demo data if the database is empty. Returns True if it seeded."""
    if (await db.execute(select(func.count()).select_from(Ward))).scalar_one():
        await seed_subscribers(db)  # databases seeded before SMS alerts existed
        await seed_field_data(db)  # ... and before the citizen and driver sections
        return False

    meta = load("meta")
    password = meta["demoPassword"]
    ward_user = load("ward_user")
    demo_ward = ward_user["ward"]

    # Wards
    status = {int(k): v for k, v in load("kmc_wardStatus").items()}
    schedule = {s["ward"]: s for s in load("kmc_schedule")}
    wards: dict[int, Ward] = {}
    for w in load("kmc_wards"):
        n = w["n"]
        wards[n] = Ward(
            n=n, tons=w["t"], vehicle_count=w["veh"], completion=w["comp"], status=status.get(n, "In Progress"),
            schedule_time=schedule[n]["time"], schedule_kind=schedule[n]["kind"],
        )
    db.add_all(wards.values())

    # Drivers
    drivers = list(dict.fromkeys(load("kmc_drivers") + load("ward_drivers")))
    db.add_all(Driver(name=d) for d in drivers)

    # Vehicles: KMC fleet, assigned to the ward whose route they run, then the
    # demo ward's own vehicles (the ward portal's version wins on conflicts).
    kmc_routes = load("kmc_routes")
    vehicle_ward = {r["v"]: r["w"] for r in kmc_routes}
    vehicles: dict[str, Vehicle] = {}
    for v in load("kmc_vehicles"):
        vehicles[v["id"]] = Vehicle(id=v["id"], driver=v["drv"], capacity=v["cap"], status=v["st"], note=v["note"], ward=vehicle_ward.get(v["id"]))
    for v in load("ward_vehicles"):
        vehicles[v["id"]] = Vehicle(id=v["id"], driver=v["drv"], capacity=v["cap"], status=v["st"], note=v["note"], ward=demo_ward)
    db.add_all(vehicles.values())

    # Routes: the demo ward gets the ward portal's routes; wards in the KMC route
    # list get `n` routes ending in their current status; every other ward gets one.
    ward_times = {s["route"]: s["time"] for s in load("ward_schedule")}
    routes: list[Route] = []
    for r in load("ward_routes"):
        routes.append(Route(ward=demo_ward, n=r["n"], vehicle=r["v"], area=r["area"], status=r["s"], kg=r["kg"], time=ward_times.get(r["n"], "08:00")))
    wards[demo_ward].tons = round(sum(r.kg for r in routes) / 1000, 2)

    kmc_route_by_ward = {r["w"]: r for r in kmc_routes if r["w"] != demo_ward}
    for n, ward in wards.items():
        if n == demo_ward:
            continue
        kr = kmc_route_by_ward.get(n, {"n": 1, "v": ""})
        count, vehicle = kr["n"], kr["v"]
        last_done = ward.status == "Completed"
        done = count if last_done else count - 1
        kg_each = round(ward.tons * 1000 / done) if done else 0
        for i in range(1, count + 1):
            completed = i <= done
            routes.append(Route(
                ward=n, n=i, vehicle=vehicle, area=f"Ward {n} zone {i}", status="Completed" if completed else ward.status,
                kg=kg_each if completed else 0, time=ward.schedule_time,
            ))
    db.add_all(routes)

    # Programs: KMC list, with the demo ward's programs merged in.
    programs: list[Program] = []
    for p in load("kmc_programs"):
        programs.append(Program(
            name=p["n"], ward=p["w"], date=p["d"], time=p["tm"], expected=p["exp"], registered=p["reg"],
            attended=p["att"], status=p["s"], approval="Approved", description=p["ds"],
        ))
    for p in load("ward_programs"):
        match = next((x for x in programs if x.ward == demo_ward and x.name == p["n"] and x.date == p["d"]), None)
        if match:
            match.location, match.approval = p.get("loc"), p.get("ap", "Approved")
            continue
        programs.append(Program(
            name=p["n"], ward=demo_ward, date=p["d"], time=p["tm"], location=p.get("loc"), expected=p["exp"],
            registered=p["reg"], attended=p["att"], status=TO_CANONICAL_PROGRAM_STATUS.get(p["s"], p["s"]),
            approval=p.get("ap", "Approved"), description=p["ds"],
        ))
    db.add_all(programs)

    # Updates and reports are listed newest first (highest id first), so insert oldest first.
    updates = [Update(category=u["c"], title=u["t"], body=u["b"], audience=u["w"], date=u["d"]) for u in load("kmc_updates")]
    updates += [Update(category=u["c"], title=u["t"], body=u["b"], audience=f"Ward {demo_ward}", date=u["d"]) for u in load("ward_updates")]
    db.add_all(sorted(updates, key=lambda u: short_date_key(u.date)))

    reports = [
        Report(type=r["ty"], ward=r["w"], source=r["src"], date=r["d"], status=r["s"], description=r["ds"], category=r["c"], notes=[])
        for r in load("kmc_reports") if r["w"] != demo_ward
    ]
    reports += [
        Report(type=r["ty"], ward=demo_ward, source=r["src"], date=r["d"], status=r["s"], route=r["rt"], description=r["ds"],
               category=r["c"], location=r["loc"], notes=r["notes"])
        for r in load("ward_reports")
    ]
    db.add_all(sorted(reports, key=lambda r: short_date_key(r.date)))

    notifications = [Notification(scope=KMC_SCOPE, text=x["text"], href=x["href"]) for x in reversed(load("kmc_notifications"))]
    notifications += [Notification(scope=ward_scope(demo_ward), text=x["text"], href=x["href"]) for x in reversed(load("ward_notifications"))]
    db.add_all(notifications)

    kmc_user = load("kmc_user")
    db.add_all([
        User(name=kmc_user["name"], role=kmc_user["role"], email=kmc_user["email"], password_hash=get_password_hash(password), portal=Portal.KMC),
        User(name=ward_user["name"], role=ward_user["role"], email=ward_user["email"], password_hash=get_password_hash(password),
             portal=Portal.WARD, ward=demo_ward),
    ])

    await db.commit()
    await seed_subscribers(db)
    await seed_field_data(db)
    return True


async def seed_subscribers(db: AsyncSession) -> None:
    """Demo SMS subscribers (fake 98000000xx numbers), if there are none yet."""
    if (await db.execute(select(func.count()).select_from(Subscriber))).scalar_one():
        return
    db.add_all(Subscriber(name=s["name"], phone=s["phone"], ward=s["ward"]) for s in load("sms_subscribers"))
    await db.commit()


DEMO_CITIZEN = {"name": "Asha Gurung", "email": "asha.gurung@example.com", "phone": "+9779800000099"}


def driver_email(name: str) -> str:
    return ".".join(name.lower().split()) + "@kathmandu.gov.np"


async def seed_field_data(db: AsyncSession) -> None:
    """Stops with coordinates, driver accounts, a demo citizen and starting truck positions.
    Each part is skipped when it already exists, so this also upgrades older databases."""
    meta = load("meta")
    demo_ward = load("ward_user")["ward"]
    password_hash = None

    def demo_hash() -> str:
        nonlocal password_hash
        password_hash = password_hash or get_password_hash(meta["demoPassword"])
        return password_hash

    # Stops for every route that has a vehicle and none yet.
    routes = list((await db.execute(select(Route).where(Route.vehicle != "").order_by(Route.ward, Route.n))).scalars())
    has_stops = set((await db.execute(select(Stop.route_id).distinct())).scalars())
    for route in routes:
        demo = DEMO_ROUTES.get(route.n) if route.ward == demo_ward else None
        if route.waste_type is None or (demo and route.waste_type == "Organic + Inorganic"):
            route.waste_type = demo["waste"] if demo else "Organic + Inorganic"
        if route.id in has_stops:
            continue
        points = demo["stops"] if demo else generated_stops(route.ward, route.n)
        done = len(points) if route.status == "Completed" else (len(points) * 3 // 7 if route.status == "In Progress" else 0)
        for i, (name, lat, lng) in enumerate(points):
            collected = i < done
            db.add(Stop(
                route_id=route.id, seq=i + 1, name=name, lat=lat, lng=lng, status="Collected" if collected else "Pending",
                collected_at=datetime.utcnow() if collected else None,
            ))
        # Park the truck at its next stop (or the last one) so the maps have something to show.
        vehicle = await db.get(Vehicle, route.vehicle)
        if vehicle is not None and vehicle.lat is None and route.status != "Upcoming":
            name, lat, lng = points[min(done, len(points) - 1)]
            vehicle.lat, vehicle.lng, vehicle.accuracy, vehicle.located_at = lat, lng, 25.0, datetime.utcnow()

    # A driver account for every driver (email first.last@kathmandu.gov.np).
    emails = set((await db.execute(select(User.email))).scalars())
    for name in (await db.execute(select(Driver.name).order_by(Driver.id))).scalars():
        email = driver_email(name)
        if email not in emails:
            db.add(User(name=name, role="Driver", email=email, password_hash=demo_hash(), portal=Portal.DRIVER))
            emails.add(email)

    if DEMO_CITIZEN["email"] not in emails:
        db.add(User(
            name=DEMO_CITIZEN["name"], role="Resident", email=DEMO_CITIZEN["email"], password_hash=demo_hash(),
            portal=Portal.CITIZEN, ward=demo_ward, phone=DEMO_CITIZEN["phone"],
        ))

    # Reports from before report history existed.
    for report in (await db.execute(select(Report).where(Report.history.is_(None)))).scalars():
        report.history = [{"status": "Pending", "at": None, "note": f"Reported {report.date}"}]
        if report.status != "Pending":
            report.history.append({"status": report.status, "at": None, "note": None})
    await db.commit()
