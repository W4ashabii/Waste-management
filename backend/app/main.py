import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session, init_db
from app import sms as sms_service
from app.routers import auth, identify, kmc, shared, sms, ward
from app.seed import seed


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    provider = sms_service.provider()
    logging.getLogger("app.sms").info(
        "SMS provider: %s%s", provider.name, " (messages are logged, not delivered)" if provider.name == "dummy" else "",
    )
    await init_db()
    if settings.SEED_ON_STARTUP:
        async with async_session() as db:
            await seed(db)
    yield


app = FastAPI(title="Kathmandu Waste Management API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, ward, kmc, shared, identify, sms):
    app.include_router(module.router)


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    model = "unavailable"
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{settings.MODEL_SERVICE_URL}/health")
            model = response.json().get("status", "unknown")
    except (httpx.HTTPError, ValueError):
        pass
    return {"status": "healthy", "model_service": model}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
