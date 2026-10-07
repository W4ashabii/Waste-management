from io import BytesIO


def image():
    return {"image": ("bottle.jpg", BytesIO(b"\xff\xd8fake-jpeg"), "image/jpeg")}


async def test_identify_anonymous(client, fake_classifier):
    r = await client.post("/api/v1/identify", files=image())
    assert r.status_code == 201
    body = r.json()
    assert body["label"] == "Bio" and body["category"] == "degradable" and body["ward"] is None
    assert fake_classifier == ["bottle.jpg"]


async def test_identify_defaults_to_staff_ward_and_lists(ward, fake_classifier):
    r = await ward.post("/api/v1/identify", files=image())
    assert r.json()["ward"] == 17
    r = await ward.get("/api/v1/identifications")
    assert r.json()["summary"] == {"total": 1, "degradable": 1, "non_degradable": 0}
    assert r.json()["items"][0]["probabilities"]["Bio"] == 0.97


async def test_ward_staff_cannot_identify_for_other_ward(ward, fake_classifier):
    r = await ward.post("/api/v1/identify", files=image(), data={"ward": "12"})
    assert r.status_code == 403


async def test_kmc_lists_all_or_by_ward(kmc, fake_classifier):
    await kmc.post("/api/v1/identify", files=image(), data={"ward": "12"})
    await kmc.post("/api/v1/identify", files=image())
    assert (await kmc.get("/api/v1/identifications")).json()["summary"]["total"] == 2
    assert (await kmc.get("/api/v1/identifications?ward=12")).json()["summary"]["total"] == 1


async def test_empty_upload_rejected(client, fake_classifier):
    r = await client.post("/api/v1/identify", files={"image": ("x.jpg", BytesIO(b""), "image/jpeg")})
    assert r.status_code == 400


async def test_model_service_down(client, monkeypatch):
    monkeypatch.setattr("app.routers.identify.settings.MODEL_SERVICE_URL", "http://127.0.0.1:9")
    r = await client.post("/api/v1/identify", files=image())
    assert r.status_code == 503
