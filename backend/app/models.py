from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    USER = "user"
    WARD_ADMIN = "ward_admin"
    MUNICIPALITY_ADMIN = "municipality_admin"


class TruckState(str, enum.Enum):
    IDLE = "idle"
    DISPATCHED = "dispatched"
    ENROUTE = "enroute"
    COLLECTING = "collecting"
    COMPLETED = "completed"


class TaskState(str, enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Municipality(Base):
    __tablename__ = "municipalities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    wards = relationship("Ward", back_populates="municipality")


class Ward(Base):
    __tablename__ = "wards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    municipality = relationship("Municipality", back_populates="wards")
    users = relationship("User", back_populates="ward")
    cameras = relationship("Camera", back_populates="ward")
    trucks = relationship("Truck", back_populates="ward_assigned")
    detection_records = relationship("DetectionRecord", back_populates="ward")
    alerts = relationship("Alert", back_populates="ward")
    truck_tasks = relationship("TruckTask", back_populates="ward")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ward = relationship("Ward", back_populates="users")


class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    location = Column(String)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ward = relationship("Ward", back_populates="cameras")
    detection_records = relationship("DetectionRecord", back_populates="camera")


class Truck(Base):
    __tablename__ = "trucks"
    
    id = Column(Integer, primary_key=True, index=True)
    plate_no = Column(String, unique=True, index=True)
    ward_id_assigned = Column(Integer, ForeignKey("wards.id"))
    state = Column(SQLEnum(TruckState), default=TruckState.IDLE)
    last_location = Column(String)
    capacity = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ward_assigned = relationship("Ward", back_populates="trucks")
    tasks = relationship("TruckTask", back_populates="truck")


class DetectionRecord(Base):
    __tablename__ = "detection_records"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    image_url = Column(String, nullable=True)
    label = Column(String)  # degradable or non_degradable
    confidence = Column(Float)
    bbox = Column(JSON)  # bounding boxes
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    camera = relationship("Camera", back_populates="detection_records")
    ward = relationship("Ward", back_populates="detection_records")
    alerts = relationship("Alert", back_populates="detection_record")


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    detection_id = Column(Integer, ForeignKey("detection_records.id"))
    severity = Column(String, default="medium")
    is_acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ward = relationship("Ward", back_populates="alerts")
    detection_record = relationship("DetectionRecord", back_populates="alerts")
    truck_tasks = relationship("TruckTask", back_populates="alert")


class TruckTask(Base):
    __tablename__ = "truck_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    truck_id = Column(Integer, ForeignKey("trucks.id"))
    ward_id = Column(Integer, ForeignKey("wards.id"))
    alert_id = Column(Integer, ForeignKey("alerts.id"))
    state = Column(SQLEnum(TaskState), default=TaskState.PENDING)
    dispatched_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    truck = relationship("Truck", back_populates="tasks")
    ward = relationship("Ward", back_populates="truck_tasks")
    alert = relationship("Alert", back_populates="truck_tasks")
