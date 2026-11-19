"""Citizen section: a resident's ward collection schedule, live truck map, programs,
reports and SMS collection reminders."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import sms
from app.auth import get_citizen_user
from app.config import settings
from app.database import get_db
from app.models import Notification, Program, Registration, Report, Subscriber, Update, User
from app.routers.live import live_data
from app.serializers import citizen_report, kmc_program, notification_out, update_out
from app.services import add_history, get_ward, notify, report_ref, today, user_scope, ward_scope

router = APIRouter(prefix="/api/v1/citizen", tags=["citizen"])

IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic", "image/heif": "heic"}
CATEGORIES = {"Collection", "Waste", "Dumping", "Schedule", "Other"}


class ReminderIn(BaseModel):
    enabled: bool
    phone: str | None = None


def my_ward(user: User) -> int:
    if user.ward is None:
        raise HTTPException(status_code=400, detail="Choose your ward first")
    return user.ward


async def reminder_on(db: AsyncSession, user: User) -> bool:
    if not user.phone or user.ward is None:
        return False
    found = await db.execute(select(Subscriber.id).where(Subscriber.ward == user.ward, Subscriber.phone == user.phone))
    return found.first() is not None


@router.get("/state")
async def state(user: User = Depends(get_citizen_user), db: AsyncSession = Depends(get_db)):
    n = my_ward(user)
    ward = await get_ward(db, n)
    updates = (await db.execute(
        select(Update).where(Update.audience.in_((f"Ward {n}", "All wards"))).order_by(Update.id.desc()).limit(40)
    )).scalars()
    programs = (await db.execute(
        select(Program).where(Program.approval == "Approved").order_by(Program.id)
    )).scalars()
    mine = set((await db.execute(select(Registration.program_id).where(Registration.user_id == user.id))).scalars())
    reports = (await db.execute(select(Report).where(Report.user_id == user.id).order_by(Report.id.desc()))).scalars()
    notifications = (await db.execute(
        select(Notification).where(Notification.scope == user_scope(user.id)).order_by(Notification.id.desc()).limit(30)
    )).scalars()
    return {
        "ward": {"n": ward.n, "status": ward.status, "time": ward.schedule_time, "kind": ward.schedule_kind},
        "live": await live_data(db, n),
        "updates": [update_out(u) for u in updates],
        "programs": [{**kmc_program(p), "mine": p.id in mine} for p in programs],
        "reports": [citizen_report(r) for r in reports],
        "notifications": [notification_out(x) for x in notifications],
        "reminder": await reminder_on(db, user),
    }


async def save_photo(photo: UploadFile) -> str:
    ext = IMAGE_TYPES.get((photo.content_type or "").lower())
    if ext is None:
        raise HTTPException(status_code=400, detail="The photo must be a JPEG, PNG, WebP or HEIC image")
    data = await photo.read(settings.MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The photo is empty")
    if len(data) > settings.MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="The photo is too large (10 MB at most)")
    folder = Path(settings.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(data)
    return name


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    type: str = Form(min_length=1, max_length=120),
    category: str = Form(default="Other"),
    description: str = Form(min_length=1, max_length=2000),
    location: str = Form(default="", max_length=200),
    route: int | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    user: User = Depends(get_citizen_user),
    db: AsyncSession = Depends(get_db),
):
    n = my_ward(user)
    report = Report(
        type=type.strip(), ward=n, source="Citizen", date=today(), status="Pending", route=route,
        description=description.strip(), category=category if category in CATEGORIES else "Other",
        location=location.strip(), notes=[], user_id=user.id,
    )
    if photo is not None and photo.filename:
        report.photo = await save_photo(photo)
    add_history(report, "Pending", "Report submitted")
    db.add(report)
    await db.flush()
    notify(db, ward_scope(n), f"New citizen report {report_ref(report.id)}: {report.type}", "/ward/reports")
    await db.commit()
    return citizen_report(report)


async def approved_program(db: AsyncSession, program_id: int) -> Program:
    program = await db.get(Program, program_id)
    if program is None or program.approval != "Approved":
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.post("/programs/{program_id}/register")
async def register(program_id: int, user: User = Depends(get_citizen_user), db: AsyncSession = Depends(get_db)):
    program = await approved_program(db, program_id)
    if program.status == "Completed":
        raise HTTPException(status_code=400, detail="This program has already taken place")
    exists = await db.execute(select(Registration.id).where(Registration.user_id == user.id, Registration.program_id == program_id))
    if exists.first() is None:
        if program.expected and program.registered >= program.expected:
            raise HTTPException(status_code=400, detail="This program is full")
        db.add(Registration(user_id=user.id, program_id=program_id))
        program.registered += 1
        await db.commit()
    return {**kmc_program(program), "mine": True}


@router.delete("/programs/{program_id}/register")
async def unregister(program_id: int, user: User = Depends(get_citizen_user), db: AsyncSession = Depends(get_db)):
    program = await approved_program(db, program_id)
    result = await db.execute(delete(Registration).where(Registration.user_id == user.id, Registration.program_id == program_id))
    if result.rowcount:
        program.registered = max(0, program.registered - 1)
        await db.commit()
    return {**kmc_program(program), "mine": False}


@router.put("/reminder")
async def reminder(body: ReminderIn, user: User = Depends(get_citizen_user), db: AsyncSession = Depends(get_db)):
    """Collection reminders are the ward's SMS alerts: turning them on subscribes the citizen's phone."""
    n = my_ward(user)
    if body.phone:
        try:
            user.phone = sms.normalize_phone(body.phone)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    if body.enabled:
        if not user.phone:
            raise HTTPException(status_code=422, detail="Add your mobile number to get reminders")
        if not await reminder_on(db, user):
            db.add(Subscriber(name=user.name, phone=user.phone, ward=n))
    elif user.phone:
        await db.execute(delete(Subscriber).where(Subscriber.ward == n, Subscriber.phone == user.phone))
    await db.commit()
    return {"enabled": await reminder_on(db, user), "phone": user.phone}
