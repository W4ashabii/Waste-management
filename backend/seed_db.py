import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import Base, User, Ward, Municipality, Truck, UserRole, TruckState
from app.auth import get_password_hash
from app.config import settings


async def seed_database():
    DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        # Check if data already exists by checking any table
        result = await session.execute(select(Municipality).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping...")
            return
        
        # Create municipality
        municipality = Municipality(name="Default Municipality")
        session.add(municipality)
        await session.commit()
        await session.refresh(municipality)
        
        # Create wards
        ward1 = Ward(name="Ward 1", municipality_id=municipality.id)
        ward2 = Ward(name="Ward 2", municipality_id=municipality.id)
        ward3 = Ward(name="Ward 3", municipality_id=municipality.id)
        session.add_all([ward1, ward2, ward3])
        await session.commit()
        await session.refresh(ward1)
        await session.refresh(ward2)
        await session.refresh(ward3)
        
        # Create users
        user1 = User(
            name="Regular User",
            email="user@example.com",
            password_hash=get_password_hash("user123"),
            role=UserRole.USER,
            ward_id=ward1.id
        )
        
        ward_admin = User(
            name="Ward Admin",
            email="ward@example.com",
            password_hash=get_password_hash("ward123"),
            role=UserRole.WARD_ADMIN,
            ward_id=ward1.id
        )
        
        municipality_admin = User(
            name="Municipality Admin",
            email="municipality@example.com",
            password_hash=get_password_hash("muni123"),
            role=UserRole.MUNICIPALITY_ADMIN
        )
        
        session.add_all([user1, ward_admin, municipality_admin])
        await session.commit()
        
        # Create trucks
        truck1 = Truck(
            plate_no="TRUCK-001",
            ward_id_assigned=ward1.id,
            state=TruckState.IDLE,
            capacity=100
        )
        truck2 = Truck(
            plate_no="TRUCK-002",
            ward_id_assigned=ward2.id,
            state=TruckState.IDLE,
            capacity=150
        )
        
        session.add_all([truck1, truck2])
        await session.commit()
        
        print("Database seeded successfully!")
        print(f"Created municipality: {municipality.name}")
        print(f"Created wards: {ward1.name}, {ward2.name}, {ward3.name}")
        print(f"Created users: user@example.com, ward@example.com, municipality@example.com")
        print(f"Created trucks: {truck1.plate_no}, {truck2.plate_no}")
        print("\nTest credentials:")
        print("User: user@example.com / user123")
        print("Ward Admin: ward@example.com / ward123")
        print("Municipality Admin: municipality@example.com / muni123")


if __name__ == "__main__":
    asyncio.run(seed_database())
