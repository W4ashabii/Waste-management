async def state(client):
    r = await client.get("/api/v1/kmc/state")
    assert r.status_code == 200
    return r.json()


async def test_kmc_only(ward):
    assert (await ward.get("/api/v1/kmc/state")).status_code == 403


async def test_kmc_state_shape(kmc):
    s = await state(kmc)
    assert len(s["wards"]) == 32 and set(s["wards"][0]) == {"n", "t", "veh", "comp"}
    assert s["wardStatus"]["12"] == "Delayed"
    assert s["schedule"]["1"] == {"t": "07:00", "k": "Organic + Inorganic"}
    assert {r["w"] for r in s["routes"]} == {5, 8, 12, 17, 21, 23, 27, 30}
    assert {p["s"] for p in s["programs"]} <= {"Upcoming", "Running", "Completed"}
    assert len(s["drivers"]) == 8


async def test_ward_portal_changes_show_in_kmc(ward, kmc):
    await ward.post("/api/v1/wards/17/routes/3/driver-update", json={"outcome": "incomplete"})
    s = await state(kmc)
    assert s["wardStatus"]["17"] == "Incomplete"
    assert s["notifications"][0]["text"] == "Route 3 incomplete in Ward 17"


async def test_complete_and_restart(kmc):
    before = next(w for w in (await state(kmc))["wards"] if w["n"] == 12)["t"]
    r = await kmc.post("/api/v1/kmc/wards/12/complete", json={"kg": 850})
    assert r.json()["status"] == "Completed"
    s = await state(kmc)
    assert next(w for w in s["wards"] if w["n"] == 12)["t"] == round(before + 0.85, 2)
    await kmc.post("/api/v1/kmc/wards/12/restart")
    assert (await state(kmc))["wardStatus"]["12"] == "In Progress"


async def test_assign_route(kmc):
    r = await kmc.put("/api/v1/kmc/wards/12/assignment", json={"vehicle": "KMC-07", "driver": "Deepak Rai"})
    assert r.json()["v"] == "KMC-07"
    s = await state(kmc)
    assert next(x for x in s["routes"] if x["w"] == 12)["v"] == "KMC-07"
    assert next(v for v in s["vehicles"] if v["id"] == "KMC-07")["drv"] == "Deepak Rai"


async def test_schedule_change_reaches_ward(kmc, ward):
    await kmc.put("/api/v1/kmc/wards/17/schedule", json={"time": "06:00", "kind": "Organic"})
    s = await state(kmc)
    assert s["schedule"]["17"] == {"t": "06:00", "k": "Organic"}
    assert s["updates"][0]["w"] == "Ward 17"
    ws = (await ward.get("/api/v1/wards/17/state")).json()
    assert ws["notifications"][0]["text"] == "Collection schedule changed by KMC"


async def test_programs_updates_reports(kmc):
    r = await kmc.post("/api/v1/kmc/programs", json={
        "name": "Compost Day", "ward": 3, "date": "2026-10-25", "time": "14:00", "description": "", "expected": 40})
    pid = r.json()["id"]
    r = await kmc.post(f"/api/v1/programs/{pid}/register", json={"count": 4})
    assert r.json()["reg"] == 4
    r = await kmc.post("/api/v1/kmc/updates", json={"category": "Guidance", "title": "Hi", "message": "", "audience": "All wards"})
    assert r.status_code == 201
    rid = (await state(kmc))["reports"][0]["id"]
    assert (await kmc.patch(f"/api/v1/reports/{rid}", json={"status": "Resolved"})).json()["s"] == "Resolved"
