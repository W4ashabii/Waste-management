async def test_health(client):
    for path in ("/health", "/api/v1/health"):
        r = await client.get(path)
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


async def test_cors_allows_frontend_origin(client):
    r = await client.options(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "content-type,authorization"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_cors_rejects_unknown_origin(client):
    r = await client.options(
        "/api/v1/auth/login",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in r.headers
