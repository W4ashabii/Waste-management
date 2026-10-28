"""SMS alerts to residents.

Messages go through the provider chosen by SMS_PROVIDER:

- "dummy" (default): logs each message and records it as sent. Nothing leaves the
  machine, so it is safe for local tests and demos.
- "sparrow": Sparrow SMS (https://sparrowsms.com), a Nepali SMS gateway. Needs
  SPARROW_SMS_TOKEN and a sender identity (SMS_SENDER) approved by Sparrow.

Every message is stored in sms_messages either way, so the portals' outbox shows
exactly what was (or, in dummy mode, would have been) delivered. To add another
gateway, write a class with `name` and `async send(phone, text) -> SendResult`
and return it from `provider()`.
"""
import logging
import re
import uuid
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import SmsMessage, Subscriber

log = logging.getLogger("app.sms")

# Nepali mobile numbers: 10 digits starting with 96, 97 or 98.
MOBILE = re.compile(r"^9[678]\d{8}$")


def normalize_phone(value: str) -> str:
    """"984-1234567", "+977 9841234567" -> "+9779841234567"."""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 13 and digits.startswith("977"):
        digits = digits[3:]
    if not MOBILE.match(digits):
        raise ValueError("Enter a Nepali mobile number, e.g. 98XXXXXXXX")
    return f"+977{digits}"


def segments(text: str) -> int:
    """SMS parts the text needs: 160 characters (153 per part when split), or 70 (67)
    when it has non-GSM characters such as Devanagari."""
    single, multi = (160, 153) if text.isascii() else (70, 67)
    return 1 if len(text) <= single else -(-len(text) // multi)


@dataclass
class SendResult:
    ok: bool
    ref: str | None = None
    error: str | None = None


class DummyProvider:
    name = "dummy"

    async def send(self, phone: str, text: str) -> SendResult:
        ref = f"dummy-{uuid.uuid4().hex[:10]}"
        log.info("[dummy] SMS to %s (%d chars, %d part(s)) ref=%s: %s", phone, len(text), segments(text), ref, text)
        return SendResult(ok=True, ref=ref)


class SparrowProvider:
    """Sparrow SMS v2 API: POST token, from, to (10-digit number), text.
    Written against Sparrow's public docs; test with one number before a broadcast."""

    name = "sparrow"

    def __init__(self, token: str, sender: str, url: str):
        if not token:
            raise RuntimeError("SMS_PROVIDER=sparrow needs SPARROW_SMS_TOKEN")
        self.token, self.sender, self.url = token, sender, url

    async def send(self, phone: str, text: str) -> SendResult:
        data = {"token": self.token, "from": self.sender, "to": phone.removeprefix("+977"), "text": text}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self.url, data=data)
        except httpx.HTTPError as exc:
            log.warning("[sparrow] SMS to %s failed: %s", phone, exc)
            return SendResult(ok=False, error=f"Network error: {exc}")
        if response.status_code != 200:
            log.warning("[sparrow] SMS to %s rejected (%s): %s", phone, response.status_code, response.text[:200])
            return SendResult(ok=False, error=f"Sparrow {response.status_code}: {response.text[:200]}")
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        log.info("[sparrow] SMS to %s accepted: %s", phone, body.get("response", response.text[:100]))
        return SendResult(ok=True, ref=str(body.get("message_id") or "") or None)


_provider: DummyProvider | SparrowProvider | None = None


def provider() -> DummyProvider | SparrowProvider:
    global _provider
    if _provider is None:
        if settings.SMS_PROVIDER == "sparrow":
            _provider = SparrowProvider(settings.SPARROW_SMS_TOKEN, settings.SMS_SENDER, settings.SPARROW_SMS_URL)
        elif settings.SMS_PROVIDER == "dummy":
            _provider = DummyProvider()
        else:
            raise RuntimeError(f"Unknown SMS_PROVIDER {settings.SMS_PROVIDER!r} (use dummy or sparrow)")
    return _provider


async def send(
    db: AsyncSession, recipients: list[tuple[str, int | None]], text: str, *, kind: str, user_id: int | None = None,
) -> list[SmsMessage]:
    """Send `text` to each (phone, ward) once and record every attempt. The caller commits."""
    p = provider()
    messages = []
    for phone, ward in dict(recipients).items():
        result = await p.send(phone, text)
        message = SmsMessage(
            phone=phone, body=text, ward=ward, kind=kind, status="sent" if result.ok else "failed",
            provider=p.name, provider_ref=result.ref, error=result.error, user_id=user_id,
        )
        db.add(message)
        messages.append(message)
    await db.flush()
    return messages


async def alert_ward(db: AsyncSession, ward: int, text: str, kind: str) -> list[SmsMessage]:
    """Automatic alert to everyone subscribed in a ward."""
    phones = (await db.execute(select(Subscriber.phone).where(Subscriber.ward == ward))).scalars()
    messages = await send(db, [(phone, ward) for phone in phones], f"KMC Waste: {text}", kind=kind)
    if messages:
        log.info("Ward %s %s alert sent to %d subscriber(s)", ward, kind, len(messages))
    return messages
