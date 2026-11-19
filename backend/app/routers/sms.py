"""SMS alerts: ward subscribers, manual broadcasts and the outbox (see app/sms.py)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import sms
from app.auth import get_current_user, get_staff_user, require_ward_access
from app.database import get_db
from app.models import Portal, SmsMessage, Subscriber, User
from app.serializers import sms_out, subscriber_out
from app.services import get_ward

router = APIRouter(prefix="/api/v1/sms", tags=["sms"], dependencies=[Depends(get_staff_user)])
log = logging.getLogger("app.sms")


class SubscriberIn(BaseModel):
    name: str = Field(default="", max_length=120)
    phone: str
    ward: int | None = None


class SendIn(BaseModel):
    message: str = Field(min_length=1, max_length=640)
    # Ward to broadcast to; KMC staff may leave it empty for every ward.
    ward: int | None = None
    # Send only to this number (a test message) instead of the ward's subscribers.
    phone: str | None = None


def phone_or_422(value: str) -> str:
    try:
        return sms.normalize_phone(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def scoped_ward(user: User, ward: int | None) -> int | None:
    """Ward staff always work on their own ward; KMC staff may pick any ward or none (all)."""
    if user.portal == Portal.WARD:
        ward = ward if ward is not None else user.ward
        if ward is None:
            raise HTTPException(status_code=400, detail="Select a ward first")
    if ward is not None:
        require_ward_access(user, ward)
    return ward


@router.get("")
async def overview(
    ward: int | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ward = scoped_ward(user, ward)
    sub_where = [Subscriber.ward == ward] if ward is not None else []
    msg_where = [SmsMessage.ward == ward] if ward is not None else []
    subscribers = (await db.execute(select(Subscriber).where(*sub_where).order_by(Subscriber.ward, Subscriber.id))).scalars()
    messages = (await db.execute(select(SmsMessage).where(*msg_where).order_by(SmsMessage.id.desc()).limit(limit))).scalars()
    counts = dict((await db.execute(select(SmsMessage.status, func.count()).where(*msg_where).group_by(SmsMessage.status))).all())
    subscribers = [subscriber_out(s) for s in subscribers]
    return {
        "provider": sms.provider().name,
        "subscribers": subscribers,
        "messages": [sms_out(m) for m in messages],
        "summary": {"subscribers": len(subscribers), "sent": counts.get("sent", 0), "failed": counts.get("failed", 0)},
    }


@router.post("/subscribers", status_code=status.HTTP_201_CREATED)
async def add_subscriber(body: SubscriberIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ward = scoped_ward(user, body.ward)
    if ward is None:
        raise HTTPException(status_code=422, detail="Choose the subscriber's ward")
    await get_ward(db, ward)
    phone = phone_or_422(body.phone)
    exists = await db.execute(select(Subscriber.id).where(Subscriber.ward == ward, Subscriber.phone == phone))
    if exists.first():
        raise HTTPException(status_code=409, detail=f"{phone} is already subscribed in Ward {ward}")
    subscriber = Subscriber(name=body.name.strip(), phone=phone, ward=ward)
    db.add(subscriber)
    await db.commit()
    log.info("Subscriber %s added to Ward %s by %s", phone, ward, user.email)
    return subscriber_out(subscriber)


@router.delete("/subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_subscriber(subscriber_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    subscriber = await db.get(Subscriber, subscriber_id)
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    require_ward_access(user, subscriber.ward)
    await db.delete(subscriber)
    await db.commit()
    log.info("Subscriber %s removed from Ward %s by %s", subscriber.phone, subscriber.ward, user.email)


@router.post("/send")
async def send(body: SendIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ward = scoped_ward(user, body.ward)
    text = body.message.strip()
    if body.phone:
        recipients, kind = [(phone_or_422(body.phone), ward)], "test"
    else:
        where = [Subscriber.ward == ward] if ward is not None else []
        rows = (await db.execute(select(Subscriber.phone, Subscriber.ward).where(*where))).all()
        if not rows:
            raise HTTPException(status_code=400, detail=f"No subscribers in {f'Ward {ward}' if ward else 'any ward'} yet")
        recipients, kind = [(phone, w) for phone, w in rows], "manual"
    messages = await sms.send(db, recipients, text, kind=kind, user_id=user.id)
    await db.commit()
    sent = sum(m.status == "sent" for m in messages)
    log.info("%s sent a %s SMS to %s: %d sent, %d failed", user.email, kind, f"Ward {ward}" if ward else "all wards",
             sent, len(messages) - sent)
    return {"sent": sent, "failed": len(messages) - sent, "messages": [sms_out(m) for m in messages]}
