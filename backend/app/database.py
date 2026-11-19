import logging

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.SQL_ECHO)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
log = logging.getLogger("app.database")


async def get_db():
    async with async_session() as session:
        yield session


def add_missing_columns(conn) -> list[str]:
    """create_all() makes new tables but never changes existing ones. Add columns that
    newer models have and an older database lacks (all such columns are nullable)."""
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())
    added = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        have = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in have:
                continue
            kind = column.type.compile(dialect=conn.dialect)
            conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {kind}'))
            added.append(f"{table.name}.{column.name}")
    return added


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        added = await conn.run_sync(add_missing_columns)
    if added:
        log.info("Added columns to an existing database: %s", ", ".join(added))
