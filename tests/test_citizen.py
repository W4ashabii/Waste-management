from io import BytesIO

from conftest import make_client


async def test_citizen_signup_needs_a_ward(client):
    body = {"email": "new@example.com", "password": "secret1", "portal": "citizen", "name": "New Resident"}
    assert (await client.post("/api/v1/auth/signup", json=body)).status_code == 422
    r = await client.post("/api/v1/auth/signup", json={**body, "ward": 12, "phone": "9841234567"})
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["portal"] == "citizen" and user["ward"] == 12 and user["phone"] == "+9779841234567"
    assert user["role"] == "Resident"


async def test_wrong_section_login_is_refused(client):
    r = await client.post("/api/v1/auth/login", json={"email": "asha.gurung@example.com", "password": "demo1234", "portal": "ward"})
    assert r.status_code == 403
    assert "citizen section" in r.json()["detail"]


async def test_citizen_state(citizen):
    s = (await citizen.get("/api/v1/citizen/state")).json()
    assert s["ward"]["n"] == 17
    assert len(s["live"]["routes"]) == 4
    assert all(len(r["stops"]) >= 5 for r in s["live"]["routes"])
    assert s["reminder"] is False
    assert any(u["w"] in ("Ward 17", "All wards") for u in s["updates"])
    assert s["programs"] and all(p["ap"] == "Approved" for p in s["programs"])


async def test_citizen_cannot_use_staff_endpoints(citizen):
    for path in ("/api/v1/wards/17/state", "/api/v1/sms", "/api/v1/kmc/state", "/api/v1/driver/state"):
        assert (await citizen.get(path)).status_code == 403, path
    assert (await citizen.patch("/api/v1/reports/1", json={"status": "Resolved"})).status_code == 403
    assert (await citizen.patch("/api/v1/vehicles/KMC-04", json={"status": "Maintenance"})).status_code == 403
    assert (await citizen.post("/api/v1/sms/send", json={"message": "spam"})).status_code == 403


async def test_report_with_photo_and_status_timeline(citizen, ward):
    files = {"photo": ("bin.jpg", BytesIO(b"\xff\xd8fake-jpeg"), "image/jpeg")}
    data = {"type": "Missed waste collection", "category": "Collection", "description": "Truck did not come", "location": "Near Police Station", "route": "3"}
    r = await citizen.post("/api/v1/citizen/reports", data=data, files=files)
    assert r.status_code == 201, r.text
    report = r.json()
    assert report["ref"].startswith("WR-") and report["status"] == "Pending" and report["route"] == 3
    assert report["history"][0]["status"] == "Pending"
    photo = await citizen.get(report["photo"])
    assert photo.status_code == 200 and photo.content == b"\xff\xd8fake-jpeg"

    # Ward staff see it and move it along; the citizen sees the timeline and a notification.
    reports = (await ward.get("/api/v1/wards/17/state")).json()["reports"]
    assert reports[0]["id"] == report["id"] and reports[0]["src"] == "Citizen"
    await ward.patch(f"/api/v1/reports/{report['id']}", json={"status": "In Progress", "note": "Team sent"})
    s = (await citizen.get("/api/v1/citizen/state")).json()
    mine = s["reports"][0]
    assert [h["status"] for h in mine["history"]] == ["Pending", "In Progress"]
    assert mine["history"][1]["note"] == "Team sent"
    assert report["ref"] in s["notifications"][0]["text"]


async def test_report_rejects_non_image(citizen):
    files = {"photo": ("x.txt", BytesIO(b"hello"), "text/plain")}
    r = await citizen.post("/api/v1/citizen/reports", data={"type": "Other", "description": "x"}, files=files)
    assert r.status_code == 400


async def test_program_registration(citizen):
    programs = (await citizen.get("/api/v1/citizen/state")).json()["programs"]
    p = next(p for p in programs if p["s"] != "Completed" and (not p["exp"] or p["reg"] < p["exp"]))
    r = await citizen.post(f"/api/v1/citizen/programs/{p['id']}/register")
    assert r.json()["mine"] is True and r.json()["reg"] == p["reg"] + 1
    r = await citizen.post(f"/api/v1/citizen/programs/{p['id']}/register")  # twice counts once
    assert r.json()["reg"] == p["reg"] + 1
    r = await citizen.delete(f"/api/v1/citizen/programs/{p['id']}/register")
    assert r.json()["mine"] is False and r.json()["reg"] == p["reg"]


async def test_reminder_subscribes_phone(citizen, ward):
    r = await citizen.put("/api/v1/citizen/reminder", json={"enabled": True, "phone": "9812345678"})
    assert r.json() == {"enabled": True, "phone": "+9779812345678"}
    phones = [s["phone"] for s in (await ward.get("/api/v1/sms")).json()["subscribers"]]
    assert "+9779812345678" in phones
    r = await citizen.put("/api/v1/citizen/reminder", json={"enabled": False})
    assert r.json()["enabled"] is False
    phones = [s["phone"] for s in (await ward.get("/api/v1/sms")).json()["subscribers"]]
    assert "+9779812345678" not in phones


async def test_citizen_can_move_ward(citizen):
    r = await citizen.patch("/api/v1/me", json={"ward": 5})
    assert r.json()["ward"] == 5
    assert (await citizen.get("/api/v1/citizen/state")).json()["ward"]["n"] == 5


async def test_citizen_identifications_are_private(citizen, kmc, fake_classifier):
    image = {"image": ("peel.jpg", BytesIO(b"\xff\xd8x"), "image/jpeg")}
    r = await citizen.post("/api/v1/identify", files=image)
    assert r.json()["ward"] == 17
    await kmc.post("/api/v1/identify", files={"image": ("a.jpg", BytesIO(b"\xff\xd8y"), "image/jpeg")}, data={"ward": "17"})
    assert (await citizen.get("/api/v1/identifications")).json()["summary"]["total"] == 1
