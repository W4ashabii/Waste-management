async def state(client, n=17):
    r = await client.get(f"/api/v1/wards/{n}/state")
    assert r.status_code == 200
    return r.json()


async def test_ward_state_matches_frontend_shape(ward):
    s = await state(ward)
    assert [r["n"] for r in s["routes"]] == [1, 2, 3, 4]
    assert set(s["routes"][0]) == {"n", "v", "area", "s", "kg"}
    assert {v["id"] for v in s["vehicles"]} == {"KMC-04", "KMC-17", "KMC-21", "KMC-33"}
    assert s["schedule"] == {"1": "07:00", "2": "08:00", "3": "08:00", "4": "13:00"}
    assert {p["s"] for p in s["programs"]} <= {"Scheduled", "Ongoing", "Completed"}
    assert all(u["w"] in ("Ward 17", "All wards") for u in s["updates"])
    assert len(s["notifications"]) == 3


async def test_ward_staff_cannot_open_other_ward(ward):
    assert (await ward.get("/api/v1/wards/12/state")).status_code == 403


async def test_kmc_can_open_any_ward(kmc):
    assert (await kmc.get("/api/v1/wards/12/state")).status_code == 200


async def test_driver_completes_route_updates_tons_and_ward_status(ward, kmc):
    before = (await state(ward))["ward"]["t"]
    await ward.post("/api/v1/wards/17/routes/3/driver-update", json={"outcome": "completed", "kg": 850})
    await ward.post("/api/v1/wards/17/routes/4/driver-update", json={"outcome": "completed", "kg": 1000})
    s = await state(ward)
    assert s["ward"]["t"] == round(before + 1.85, 2)
    assert s["ward"]["status"] == "Completed"


async def test_vehicle_problem_creates_report_and_notifies_kmc(ward):
    r = await ward.post("/api/v1/wards/17/routes/3/driver-update", json={"outcome": "delayed"})
    assert r.json()["s"] == "Delayed"
    s = await state(ward)
    assert s["reports"][0]["ty"] == "Vehicle breakdown" and s["reports"][0]["rt"] == 3
    assert s["ward"]["status"] == "Delayed"
    assert s["notifications"][0]["text"].startswith("Route 3 delayed")


async def test_schedule_change_posts_update(ward):
    await ward.patch("/api/v1/wards/17/routes/3", json={"time": "09:30"})
    s = await state(ward)
    assert s["schedule"]["3"] == "09:30"
    assert s["updates"][0]["t"] == "Collection timing changed for Route 3"
    assert s["updates"][0]["b"] == "Previous: 8:00 AM → New: 9:30 AM"


async def test_assign_vehicle_and_driver(ward):
    await ward.patch("/api/v1/wards/17/routes/4", json={"vehicle": "KMC-33"})
    r = await ward.patch("/api/v1/vehicles/KMC-33", json={"driver": "Suman Tamang", "status": "Maintenance"})
    assert r.json()["drv"] == "Suman Tamang" and r.json()["st"] == "Maintenance"
    s = await state(ward)
    assert next(x for x in s["routes"] if x["n"] == 4)["v"] == "KMC-33"
    # KMC-01 belongs to Ward 5.
    assert (await ward.patch("/api/v1/vehicles/KMC-01", json={"driver": "X"})).status_code == 403


async def test_add_vehicle(ward):
    r = await ward.post("/api/v1/wards/17/vehicles", json={"id": "KMC-40", "drv": "Ram Thapa", "cap": 5, "st": "Active", "note": "New"})
    assert r.status_code == 201
    assert (await ward.post("/api/v1/wards/17/vehicles", json={"id": "KMC-40"})).status_code == 409


async def test_program_review_flow(ward, client):
    r = await ward.post("/api/v1/wards/17/programs", json={
        "name": "River Clean-up", "date": "2026-11-01", "time": "09:00", "location": "Bagmati",
        "description": "", "expected": 80, "needsCoordination": True})
    p = r.json()
    assert p["ap"] == "Pending KMC review" and p["tm"] == "9:00 AM"
    r = await ward.post(f"/api/v1/programs/{p['id']}/decision", json={"approve": True})
    assert r.json()["ap"] == "Approved"
    s = await state(ward)
    assert s["updates"][0]["t"] == "River Clean-up in Ward 17"

    await ward.post(f"/api/v1/programs/{p['id']}/start")
    await ward.post(f"/api/v1/programs/{p['id']}/complete", json={"attended": 61})
    prog = next(x for x in (await state(ward))["programs"] if x["id"] == p["id"])
    assert prog["s"] == "Completed" and prog["att"] == 61


async def test_complaint_and_report_notes(ward):
    r = await ward.post("/api/v1/wards/17/reports", json={
        "type": "Collection not completed", "source": "Citizen", "route": 4,
        "description": "Truck did not arrive.", "category": "Collection", "location": "Gaushala"})
    rid = r.json()["id"]
    r = await ward.patch(f"/api/v1/reports/{rid}", json={"status": "In Progress", "note": "Called the driver"})
    assert r.json()["s"] == "In Progress" and r.json()["notes"] == ["Called the driver"]
