"""Create tables and seed demo data. Usage: python seed_db.py [--reset]"""
import asyncio
import sys

from app.database import async_session, engine, init_db
from app.models import Base
from app.seed import seed


async def main(reset: bool) -> None:
    if reset:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    async with async_session() as db:
        print("Seeded demo data." if await seed(db) else "Database already has data; nothing to do (use --reset).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--reset" in sys.argv))
