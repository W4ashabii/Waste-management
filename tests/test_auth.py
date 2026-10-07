from conftest import DEMO_PASSWORD, KMC_EMAIL, WARD_EMAIL


async def test_login_returns_token_and_user(client):
    r = await client.post("/api/v1/auth/login", json={"email": KMC_EMAIL, "password": DEMO_PASSWORD, "portal": "kmc"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["name"] == "Anita Shrestha"
    assert body["user"]["portal"] == "kmc"


async def test_login_wrong_password(client):
    r = await client.post("/api/v1/auth/login", json={"email": KMC_EMAIL, "password": "nope", "portal": "kmc"})
    assert r.status_code == 401


async def test_login_wrong_portal(client):
    r = await client.post("/api/v1/auth/login", json={"email": WARD_EMAIL, "password": DEMO_PASSWORD, "portal": "kmc"})
    assert r.status_code == 403


async def test_signup_then_select_ward(client):
    r = await client.post("/api/v1/auth/signup", json={
        "name": "New Staff", "role": "", "email": "New@Example.com", "password": "secret1", "portal": "ward"})
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["email"] == "new@example.com" and user["role"] == "Ward Staff" and user["ward"] is None
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    r = await client.patch("/api/v1/me", json={"ward": 5})
    assert r.json()["ward"] == 5
    assert (await client.get("/api/v1/wards/5/state")).status_code == 200
    assert (await client.get("/api/v1/wards/17/state")).status_code == 403


async def test_signup_duplicate_email(client):
    r = await client.post("/api/v1/auth/signup", json={
        "name": "X", "email": KMC_EMAIL, "password": "secret1", "portal": "kmc"})
    assert r.status_code == 400


async def test_requires_auth(client):
    assert (await client.get("/api/v1/me")).status_code == 401
    assert (await client.get("/api/v1/kmc/state")).status_code == 401


async def test_update_profile_and_password(ward):
    r = await ward.patch("/api/v1/me", json={"name": "Binod M.", "role": "Ward Chair"})
    assert r.json()["name"] == "Binod M." and r.json()["role"] == "Ward Chair"

    r = await ward.post("/api/v1/me/password", json={"current_password": "bad", "new_password": "newpass1"})
    assert r.status_code == 400
    r = await ward.post("/api/v1/me/password", json={"current_password": DEMO_PASSWORD, "new_password": "newpass1"})
    assert r.status_code == 204
    r = await ward.post("/api/v1/auth/login", json={"email": WARD_EMAIL, "password": "newpass1", "portal": "ward"})
    assert r.status_code == 200
