"""Database models. Field names follow the domain; app/serializers.py maps them to
the short keys the Next.js frontend uses (n, t, drv, st, ...)."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Portal:
    KMC = "kmc"
    WARD = "ward"
    # Residents using the mobile citizen app.
    CITIZEN = "citizen"
    # Collection-vehicle drivers using the mobile driver app. A driver account is
    # linked to vehicles by name (Vehicle.driver == User.name).
    DRIVER = "driver"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120))  # job title shown in the UI
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    portal: Mapped[str] = mapped_column(String(10))  # Portal.KMC | Portal.WARD
    ward: Mapped[int | None] = mapped_column(ForeignKey("wards.n"), nullable=True)
    # Citizens: number for collection reminders (E.164). Optional.
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Ward(Base):
    __tablename__ = "wards"

    n: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    tons: Mapped[float] = mapped_column(Float, default=0)
    vehicle_count: Mapped[int] = mapped_column(Integer, default=0)
    completion: Mapped[int] = mapped_column(Integer, default=0)
    # Today's collection status: Completed | In Progress | Delayed | Incomplete
    status: Mapped[str] = mapped_column(String(20), default="In Progress")
    schedule_time: Mapped[str] = mapped_column(String(5), default="08:00")
    schedule_kind: Mapped[str] = mapped_column(String(40), default="Organic + Inorganic")


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # plate, e.g. KMC-04
    driver: Mapped[str] = mapped_column(String(120), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active | Idle | Maintenance
    note: Mapped[str] = mapped_column(String(255), default="")
    ward: Mapped[int | None] = mapped_column(ForeignKey("wards.n"), nullable=True)
    # Last GPS fix sent from the driver section.
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)  # metres
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)  # degrees
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)  # m/s
    located_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (UniqueConstraint("ward", "n"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ward: Mapped[int] = mapped_column(ForeignKey("wards.n"), index=True)
    n: Mapped[int] = mapped_column(Integer)
    vehicle: Mapped[str] = mapped_column(String(20), default="")
    area: Mapped[str] = mapped_column(String(120), default="")
    # Upcoming | In Progress | Completed | Delayed | Incomplete
    status: Mapped[str] = mapped_column(String(20), default="Upcoming")
    kg: Mapped[int] = mapped_column(Integer, default=0)
    time: Mapped[str] = mapped_column(String(5), default="08:00")
    waste_type: Mapped[str | None] = mapped_column(String(40), nullable=True, default="Organic + Inorganic")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Stop(Base):
    """A collection point on a route, in the order the truck visits it."""

    __tablename__ = "stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending | Collected | Skipped
    collected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    ward: Mapped[int] = mapped_column(ForeignKey("wards.n"), index=True)
    date: Mapped[str] = mapped_column(String(40))
    time: Mapped[str] = mapped_column(String(20))
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expected: Mapped[int] = mapped_column(Integer, default=0)
    registered: Mapped[int] = mapped_column(Integer, default=0)
    attended: Mapped[int] = mapped_column(Integer, default=0)
    # Canonical status: Upcoming | Running | Completed (the ward portal calls
    # these Scheduled | Ongoing | Completed; see serializers.py).
    status: Mapped[str] = mapped_column(String(20), default="Upcoming")
    # Approved | Pending KMC review | Needs changes
    approval: Mapped[str] = mapped_column(String(40), default="Approved")
    description: Mapped[str] = mapped_column(Text, default="")


class Update(Base):
    __tablename__ = "updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    audience: Mapped[str] = mapped_column(String(40), default="All wards")  # "All wards" | "Ward 17"
    date: Mapped[str] = mapped_column(String(20))


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(120))
    ward: Mapped[int] = mapped_column(ForeignKey("wards.n"), index=True)
    source: Mapped[str] = mapped_column(String(40))
    date: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending | In Progress | Resolved
    route: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="Other")
    location: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[list] = mapped_column(JSON, default=list)
    # Who filed it (citizen or driver account), if anyone.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    photo: Mapped[str | None] = mapped_column(String(80), nullable=True)  # file name in UPLOAD_DIR
    # [{"status": "Pending", "at": "2026-10-22T09:45:00Z", "note": "..."}], oldest first.
    history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.utcnow)


class Registration(Base):
    """A citizen registered for an awareness program."""

    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("user_id", "program_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # "kmc" for the KMC portal, "ward:<n>" for one ward's portal, "user:<id>" for one
    # citizen or driver.
    scope: Mapped[str] = mapped_column(String(20), index=True)
    text: Mapped[str] = mapped_column(String(255))
    href: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Identification(Base):
    """One photo classified by the waste model."""

    __tablename__ = "identifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    ward: Mapped[int | None] = mapped_column(ForeignKey("wards.n"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    label: Mapped[str] = mapped_column(String(20))  # model class: Bio | Non_Bio
    category: Mapped[str] = mapped_column(String(20))  # degradable | non_degradable
    confidence: Mapped[float] = mapped_column(Float)
    probabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Subscriber(Base):
    """A resident who gets SMS alerts for their ward."""

    __tablename__ = "subscribers"
    __table_args__ = (UniqueConstraint("ward", "phone"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), index=True)  # E.164, e.g. +9779841234567
    ward: Mapped[int] = mapped_column(ForeignKey("wards.n"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SmsMessage(Base):
    """One SMS to one phone number: the outbox and delivery log."""

    __tablename__ = "sms_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)
    ward: Mapped[int | None] = mapped_column(ForeignKey("wards.n"), nullable=True, index=True)
    # manual | test | schedule | delay | program
    kind: Mapped[str] = mapped_column(String(20), default="manual")
    status: Mapped[str] = mapped_column(String(10))  # sent | failed
    provider: Mapped[str] = mapped_column(String(20))
    provider_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
