import pytest

from app import sms


def test_normalize_phone():
    assert sms.normalize_phone("984-1234567") == "+9779841234567"
    assert sms.normalize_phone("+977 9841234567") == "+9779841234567"
    for bad in ("12345", "01-4412345", "+1 415 555 0100"):
        with pytest.raises(ValueError):
            sms.normalize_phone(bad)


def test_segments():
    assert sms.segments("a" * 160) == 1
    assert sms.segments("a" * 161) == 2
    assert sms.segments("फोहोर" * 15) == 2  # 75 Devanagari characters: 70 per part


async def test_ward_overview_lists_own_subscribers(ward):
    r = await ward.get("/api/v1/sms")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "dummy"
    assert body["summary"]["subscribers"] == 5
    assert {s["ward"] for s in body["subscribers"]} == {17}


async def test_ward_staff_cannot_see_other_ward(ward):
    assert (await ward.get("/api/v1/sms?ward=12")).status_code == 403


async def test_add_and_remove_subscriber(ward):
    r = await ward.post("/api/v1/sms/subscribers", json={"name": "Test", "phone": "9841234567"})
    assert r.status_code == 201 and r.json()["phone"] == "+9779841234567" and r.json()["ward"] == 17
    dup = await ward.post("/api/v1/sms/subscribers", json={"phone": "+977-9841234567"})
    assert dup.status_code == 409
    assert (await ward.post("/api/v1/sms/subscribers", json={"phone": "12345"})).status_code == 422
    assert (await ward.delete(f"/api/v1/sms/subscribers/{r.json()['id']}")).status_code == 204
    assert (await ward.get("/api/v1/sms")).json()["summary"]["subscribers"] == 5


async def test_broadcast_to_ward_is_recorded(ward):
    r = await ward.post("/api/v1/sms/send", json={"message": "Bring out your bins by 7 AM."})
    assert r.json()["sent"] == 5 and r.json()["failed"] == 0
    body = (await ward.get("/api/v1/sms")).json()
    assert body["summary"]["sent"] == 5
    assert all(m["kind"] == "manual" and m["provider"] == "dummy" and m["ref"].startswith("dummy-") for m in body["messages"])


async def test_test_message_to_one_number(ward):
    r = await ward.post("/api/v1/sms/send", json={"message": "Test", "phone": "9812345678"})
    assert r.json()["sent"] == 1 and r.json()["messages"][0]["kind"] == "test"


async def test_kmc_broadcast_to_all_wards(kmc):
    r = await kmc.post("/api/v1/sms/send", json={"message": "City-wide notice"})
    assert r.json()["sent"] == 8
    wards = {m["ward"] for m in r.json()["messages"]}
    assert wards == {5, 12, 17}


async def test_send_to_ward_without_subscribers(kmc):
    r = await kmc.post("/api/v1/sms/send", json={"message": "Hello", "ward": 1})
    assert r.status_code == 400


async def test_route_delay_alerts_subscribers(ward):
    await ward.post("/api/v1/wards/17/routes/1/driver-update", json={"outcome": "delayed"})
    messages = (await ward.get("/api/v1/sms")).json()["messages"]
    assert len(messages) == 5 and all(m["kind"] == "delay" for m in messages)
    assert messages[0]["body"].startswith("KMC Waste: Collection on Route 1")


async def test_kmc_schedule_change_alerts_ward(kmc):
    await kmc.put("/api/v1/kmc/wards/12/schedule", json={"time": "09:30", "kind": "Organic"})
    messages = (await kmc.get("/api/v1/sms?ward=12")).json()["messages"]
    assert len(messages) == 2 and "to 9:30 AM" in messages[0]["body"]


async def test_failed_send_is_recorded(ward, monkeypatch):
    async def fail(phone, text):
        return sms.SendResult(ok=False, error="gateway down")

    monkeypatch.setattr(sms.provider(), "send", fail)
    r = await ward.post("/api/v1/sms/send", json={"message": "Hi"})
    assert r.json() == {**r.json(), "sent": 0, "failed": 5}
    assert (await ward.get("/api/v1/sms")).json()["messages"][0]["error"] == "gateway down"
