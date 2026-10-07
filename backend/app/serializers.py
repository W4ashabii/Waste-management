"""Convert models to the JSON shapes used by the Next.js frontend (src/types)."""
from datetime import datetime

from app.models import Identification, Notification, Program, Report, Route, Update, User, Vehicle, Ward

# Canonical program status -> ward portal wording.
WARD_PROGRAM_STATUS = {"Upcoming": "Scheduled", "Running": "Ongoing", "Completed": "Completed"}


def today_short(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"{now:%b} {now.day}"


def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "role": u.role, "email": u.email, "portal": u.portal, "ward": u.ward}


def ward_stat(w: Ward) -> dict:
    return {"n": w.n, "t": round(w.tons, 2), "veh": w.vehicle_count, "comp": w.completion}


def vehicle_out(v: Vehicle) -> dict:
    return {"id": v.id, "drv": v.driver, "cap": v.capacity, "st": v.status, "note": v.note, "ward": v.ward}


def ward_route(r: Route) -> dict:
    return {"n": r.n, "v": r.vehicle, "area": r.area, "s": r.status, "kg": r.kg}


def kmc_program(p: Program) -> dict:
    return {
        "id": p.id, "n": p.name, "w": p.ward, "d": p.date, "tm": p.time, "exp": p.expected,
        "reg": p.registered, "att": p.attended, "s": p.status, "ds": p.description,
        "loc": p.location, "ap": p.approval,
    }


def ward_program(p: Program) -> dict:
    return {
        "id": p.id, "n": p.name, "d": p.date, "tm": p.time, "loc": p.location, "exp": p.expected,
        "reg": p.registered, "att": p.attended, "s": WARD_PROGRAM_STATUS.get(p.status, p.status),
        "ap": p.approval, "ds": p.description,
    }


def update_out(u: Update) -> dict:
    return {"id": u.id, "c": u.category, "t": u.title, "b": u.body, "w": u.audience, "d": u.date}


def kmc_report(r: Report) -> dict:
    return {
        "id": r.id, "ty": r.type, "w": r.ward, "src": r.source, "d": r.date, "s": r.status,
        "ds": r.description, "c": r.category, "rt": r.route, "loc": r.location, "notes": r.notes or [],
    }


def ward_report(r: Report) -> dict:
    return {
        "id": r.id, "ty": r.type, "src": r.source, "d": r.date, "s": r.status, "rt": r.route or 0,
        "ds": r.description, "c": r.category, "loc": r.location, "notes": r.notes or [],
    }


def notification_out(n: Notification) -> dict:
    return {"id": n.id, "text": n.text, "href": n.href}


def identification_out(i: Identification) -> dict:
    return {
        "id": i.id, "ward": i.ward, "label": i.label, "category": i.category, "confidence": i.confidence,
        "probabilities": i.probabilities or {}, "filename": i.filename, "created_at": i.created_at.isoformat() + "Z",
    }
