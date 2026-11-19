"""Convert models to the JSON shapes used by the Next.js frontend (src/types)."""
from datetime import datetime

from app.models import (
    Identification, Notification, Program, Report, Route, SmsMessage, Stop, Subscriber, Update, User, Vehicle, Ward,
)
from app.services import iso, report_ref

# Canonical program status -> ward portal wording.
WARD_PROGRAM_STATUS = {"Upcoming": "Scheduled", "Running": "Ongoing", "Completed": "Completed"}


def today_short(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"{now:%b} {now.day}"


def user_out(u: User) -> dict:
    return {
        "id": u.id, "name": u.name, "role": u.role, "email": u.email, "portal": u.portal, "ward": u.ward, "phone": u.phone,
    }


def ward_stat(w: Ward) -> dict:
    return {"n": w.n, "t": round(w.tons, 2), "veh": w.vehicle_count, "comp": w.completion}


def vehicle_out(v: Vehicle) -> dict:
    return {"id": v.id, "drv": v.driver, "cap": v.capacity, "st": v.status, "note": v.note, "ward": v.ward}


def location_out(v: Vehicle) -> dict | None:
    if v.lat is None or v.lng is None:
        return None
    return {
        "lat": v.lat, "lng": v.lng, "accuracy": v.accuracy, "heading": v.heading, "speed": v.speed, "at": iso(v.located_at),
    }


def stop_out(s: Stop) -> dict:
    return {"id": s.id, "seq": s.seq, "name": s.name, "lat": s.lat, "lng": s.lng, "status": s.status, "at": iso(s.collected_at)}


def route_detail(r: Route, stops: list[Stop]) -> dict:
    """A route with its stops, for the maps and the driver and citizen apps."""
    return {
        "id": r.id, "ward": r.ward, "n": r.n, "vehicle": r.vehicle, "area": r.area, "status": r.status, "kg": r.kg,
        "time": r.time, "waste": r.waste_type or "Organic + Inorganic", "started_at": iso(r.started_at),
        "completed_at": iso(r.completed_at), "stops": [stop_out(s) for s in stops],
    }


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


def report_extra(r: Report) -> dict:
    return {
        "ref": report_ref(r.id), "photo": f"/api/v1/uploads/{r.photo}" if r.photo else None,
        "history": r.history or [], "at": iso(r.created_at),
    }


def kmc_report(r: Report) -> dict:
    return {
        "id": r.id, "ty": r.type, "w": r.ward, "src": r.source, "d": r.date, "s": r.status,
        "ds": r.description, "c": r.category, "rt": r.route, "loc": r.location, "notes": r.notes or [], **report_extra(r),
    }


def ward_report(r: Report) -> dict:
    return {
        "id": r.id, "ty": r.type, "src": r.source, "d": r.date, "s": r.status, "rt": r.route or 0,
        "ds": r.description, "c": r.category, "loc": r.location, "notes": r.notes or [], **report_extra(r),
    }


def citizen_report(r: Report) -> dict:
    return {
        "id": r.id, "type": r.type, "ward": r.ward, "date": r.date, "status": r.status, "route": r.route,
        "description": r.description, "category": r.category, "location": r.location, **report_extra(r),
    }


def notification_out(n: Notification) -> dict:
    return {"id": n.id, "text": n.text, "href": n.href}


def identification_out(i: Identification) -> dict:
    return {
        "id": i.id, "ward": i.ward, "label": i.label, "category": i.category, "confidence": i.confidence,
        "probabilities": i.probabilities or {}, "filename": i.filename, "created_at": i.created_at.isoformat() + "Z",
    }


def subscriber_out(s: Subscriber) -> dict:
    return {"id": s.id, "name": s.name, "phone": s.phone, "ward": s.ward, "created_at": s.created_at.isoformat() + "Z"}


def sms_out(m: SmsMessage) -> dict:
    return {
        "id": m.id, "phone": m.phone, "body": m.body, "ward": m.ward, "kind": m.kind, "status": m.status,
        "provider": m.provider, "ref": m.provider_ref, "error": m.error, "created_at": m.created_at.isoformat() + "Z",
    }
