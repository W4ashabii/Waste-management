async def driver_state(driver):
    r = await driver.get("/api/v1/driver/state")
    assert r.status_code == 200
    return r.json()


async def test_driver_sees_routes_of_own_vehicles(driver):
    s = await driver_state(driver)
    assert {v["id"] for v in s["vehicles"]} == {"KMC-01", "KMC-04"}
    assert s["routes"][0]["status"] == "In Progress"  # in-progress routes first
    assert all(r["vehicle"] in ("KMC-01", "KMC-04") for r in s["routes"])
    baneshwor = next(r for r in s["routes"] if r["ward"] == 17)
    assert baneshwor["area"] == "Baneshwor" and baneshwor["stops"][0]["name"] == "New Baneshwor Chowk"


async def test_location_moves_vehicle_and_shows_on_live_map(driver, ward, citizen):
    r = await driver.post("/api/v1/driver/location", json={"lat": 27.0, "lng": 85.0})
    assert r.json()["vehicle"] in ("KMC-01", "KMC-04")  # a vehicle with a route in progress
    r = await driver.post("/api/v1/driver/location", json={"lat": 27.69, "lng": 85.335, "accuracy": 12, "speed": 4.5, "vehicle": "KMC-04"})
    assert r.json()["vehicle"] == "KMC-04"
    r = await driver.post("/api/v1/driver/location", json={"lat": 27.69, "lng": 85.335, "vehicle": "KMC-17"})
    assert r.json()["vehicle"] != "KMC-17"  # not one of this driver's vehicles
    live = (await ward.get("/api/v1/live")).json()
    truck = next(v for v in live["vehicles"] if v["id"] == "KMC-04")
    assert truck["location"]["lat"] == 27.69 and truck["location"]["speed"] == 4.5
    assert (await citizen.get("/api/v1/live")).json()["vehicles"]  # citizens see their ward's trucks
    bad = await driver.post("/api/v1/driver/location", json={"lat": 120, "lng": 85})
    assert bad.status_code == 422


async def test_full_route_flow(driver, ward):
    s = await driver_state(driver)
    route = next(r for r in s["routes"] if r["ward"] == 17)
    pending = [x for x in route["stops"] if x["status"] == "Pending"]
    r = await driver.post(f"/api/v1/driver/stops/{pending[0]['id']}", json={"status": "Collected"})
    assert next(x for x in r.json()["stops"] if x["id"] == pending[0]["id"])["status"] == "Collected"
    r = await driver.post(f"/api/v1/driver/stops/{pending[1]['id']}", json={"status": "Skipped"})
    assert r.status_code == 200

    assert (await driver.post(f"/api/v1/driver/routes/{route['id']}/finish", json={"outcome": "completed", "kg": 0})).status_code == 422
    r = await driver.post(f"/api/v1/driver/routes/{route['id']}/finish", json={"outcome": "completed", "kg": 900})
    done = r.json()
    assert done["status"] == "Completed" and done["kg"] == 900 and done["completed_at"]
    assert all(x["status"] != "Pending" for x in done["stops"])
    routes = (await ward.get("/api/v1/wards/17/state")).json()["routes"]
    assert next(x for x in routes if x["n"] == route["n"])["s"] == "Completed"


async def test_start_route_and_stop_rules(driver):
    s = await driver_state(driver)
    other = next(r for r in s["routes"] if r["ward"] != 17)
    if other["status"] == "Upcoming":
        stop = other["stops"][0]
        assert (await driver.post(f"/api/v1/driver/stops/{stop['id']}", json={"status": "Collected"})).status_code == 400
    r = await driver.post(f"/api/v1/driver/routes/{other['id']}/start")
    if other["status"] == "Completed":
        assert r.status_code == 400
    else:
        assert r.json()["status"] == "In Progress" and r.json()["started_at"]


async def test_driver_cannot_touch_other_routes(driver, ward):
    # Route 1 of Ward 17 runs on KMC-17 (Sita Gurung), not Ram Thapa's vehicles.
    live = (await ward.get("/api/v1/live")).json()
    foreign = next(r for r in live["routes"] if r["vehicle"] == "KMC-17")
    assert (await driver.post(f"/api/v1/driver/routes/{foreign['id']}/start")).status_code == 404
    assert (await driver.post(f"/api/v1/driver/stops/{foreign['stops'][0]['id']}", json={"status": "Pending"})).status_code == 404
    assert (await driver.get("/api/v1/wards/17/state")).status_code == 403


async def test_delayed_route_creates_report_and_sms(driver, ward):
    s = await driver_state(driver)
    route = next(r for r in s["routes"] if r["ward"] == 17)
    r = await driver.post(f"/api/v1/driver/routes/{route['id']}/finish", json={"outcome": "delayed"})
    assert r.json()["status"] == "Delayed"
    state = (await ward.get("/api/v1/wards/17/state")).json()
    assert state["reports"][0]["ty"] == "Vehicle breakdown"
    outbox = (await ward.get("/api/v1/sms")).json()["messages"]
    assert any(m["kind"] == "delay" for m in outbox)


async def test_issue_report(driver, ward):
    r = await driver.post("/api/v1/driver/issues", json={"type": "Brake problem", "description": "Squeaking", "vehicle": "KMC-04"})
    assert r.status_code == 201
    assert r.json()["c"] == "Vehicle" and r.json()["ds"].startswith("KMC-04")
    assert (await driver_state(driver))["issues"][0]["ty"] == "Brake problem"
    assert (await ward.get("/api/v1/wards/17/state")).json()["reports"][0]["ty"] == "Brake problem"


async def test_driver_signup_registers_driver_name(client, ward):
    body = {"email": "new.driver@example.com", "password": "secret1", "portal": "driver", "name": "Maya Lama"}
    assert (await client.post("/api/v1/auth/signup", json=body)).status_code == 201
    assert "Maya Lama" in (await ward.get("/api/v1/wards/17/state")).json()["drivers"]


async def test_driver_cannot_rename(driver):
    assert (await driver.patch("/api/v1/me", json={"name": "Someone Else"})).status_code == 400


async def test_kmc_live_city_wide(kmc):
    live = (await kmc.get("/api/v1/live")).json()
    assert len(live["centres"]) == 32
    assert {r["ward"] for r in live["routes"]} >= {17, 8, 5}
