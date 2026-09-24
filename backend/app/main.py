from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import httpx
from app.database import get_db, init_db
from app.models import (
    User, Ward, Municipality, Camera, Truck, DetectionRecord, 
    Alert, TruckTask, UserRole, TruckState, TaskState
)
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_ward_admin, get_municipality_admin, check_ward_access
)
from app.config import settings
from pydantic import BaseModel

app = FastAPI(title="Waste Management API")


# Pydantic models for requests/responses
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole
    ward_id: Optional[int] = None


class DetectionResponse(BaseModel):
    label: str
    confidence: float
    bboxes: List[dict]
    detection_id: int


class TruckDispatchRequest(BaseModel):
    ward_id: int
    alert_id: int


class TruckStateUpdate(BaseModel):
    state: TruckState


class AlertResponse(BaseModel):
    id: int
    ward_id: int
    detection_id: int
    severity: str
    is_acknowledged: bool
    created_at: datetime


class TruckResponse(BaseModel):
    id: int
    plate_no: str
    ward_id_assigned: Optional[int]
    state: str
    last_location: Optional[str]
    capacity: int


class AnalyticsResponse(BaseModel):
    ward_id: int
    date: str
    degradable_count: int
    non_degradable_count: int


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "ward_id": user.ward_id
        }
    }


@app.post("/api/v1/auth/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        ward_id=user_data.ward_id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {"message": "User created successfully", "user_id": user.id}


@app.post("/api/v1/detect", response_model=DetectionResponse)
async def detect(
    image: UploadFile = File(...),
    camera_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    # Forward to model service
    async with httpx.AsyncClient() as client:
        files = {"image": (image.filename, image.file, image.content_type)}
        response = await client.post(
            f"{settings.MODEL_SERVICE_URL}/detect",
            files=files
        )
        model_result = response.json()
    
    # Load label mapping (path relative to this module, not the CWD)
    label_mapping_path = Path(__file__).parent / "label_mapping.json"
    with open(label_mapping_path, "r") as f:
        label_mapping = json.load(f)
    
    # Map model labels to degradable/non_degradable
    predictions = model_result["predictions"]
    if predictions:
        first_pred = predictions[0]
        model_label = first_pred["label"]
        category = label_mapping.get(model_label, "non_degradable")
        confidence = first_pred["confidence"]
        bbox = [{"x": first_pred["bbox"][0], "y": first_pred["bbox"][1], 
                "w": first_pred["bbox"][2], "h": first_pred["bbox"][3]}]
    else:
        category = "non_degradable"
        confidence = 0.0
        bbox = []
    
    # Get or create camera and ward
    if camera_id:
        camera_result = await db.execute(select(Camera).where(Camera.name == camera_id))
        camera = camera_result.scalar_one_or_none()
        if not camera:
            # Create camera with default ward
            ward_result = await db.execute(select(Ward).limit(1))
            ward = ward_result.scalar_one_or_none()
            if not ward:
                # Create default ward
                ward = Ward(name="Default Ward")
                db.add(ward)
                await db.commit()
                await db.refresh(ward)
            
            camera = Camera(name=camera_id, ward_id=ward.id, location="Unknown")
            db.add(camera)
            await db.commit()
            await db.refresh(camera)
        ward_id = camera.ward_id
    else:
        # Use first ward
        ward_result = await db.execute(select(Ward).limit(1))
        ward = ward_result.scalar_one_or_none()
        if not ward:
            ward = Ward(name="Default Ward")
            db.add(ward)
            await db.commit()
            await db.refresh(ward)
        ward_id = ward.id
        camera = None
    
    # Store detection record
    detection = DetectionRecord(
        camera_id=camera.id if camera else None,
        ward_id=ward_id,
        label=category,
        confidence=confidence,
        bbox=bbox
    )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)
    
    # Check if threshold exceeded and create alert
    # TODO: Implement proper threshold logic based on count in area
    if confidence > 0.7:
        alert = Alert(
            ward_id=ward_id,
            detection_id=detection.id,
            severity="high" if confidence > 0.9 else "medium"
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        
        # Broadcast alert via WebSocket
        await manager.broadcast({
            "type": "alert",
            "data": {
                "id": alert.id,
                "ward_id": alert.ward_id,
                "detection_id": alert.detection_id,
                "severity": alert.severity,
                "label": category,
                "confidence": confidence
            }
        })
    
    return {
        "label": category,
        "confidence": confidence,
        "bboxes": bbox,
        "detection_id": detection.id
    }


@app.get("/api/v1/trucks", response_model=List[TruckResponse])
async def get_trucks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == "municipality_admin":
        result = await db.execute(select(Truck))
    elif current_user.role == "ward_admin":
        result = await db.execute(select(Truck).where(Truck.ward_id_assigned == current_user.ward_id))
    else:
        result = await db.execute(select(Truck).where(Truck.ward_id_assigned == current_user.ward_id))
    
    trucks = result.scalars().all()
    return [
        {
            "id": truck.id,
            "plate_no": truck.plate_no,
            "ward_id_assigned": truck.ward_id_assigned,
            "state": truck.state.value,
            "last_location": truck.last_location,
            "capacity": truck.capacity
        }
        for truck in trucks
    ]


@app.post("/api/v1/trucks/{truck_id}/dispatch")
async def dispatch_truck(
    truck_id: int,
    request: TruckDispatchRequest,
    current_user: User = Depends(get_ward_admin),
    db: AsyncSession = Depends(get_db)
):
    # Check ward access
    if not check_ward_access(current_user, request.ward_id):
        raise HTTPException(status_code=403, detail="Not authorized for this ward")
    
    # Get truck
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck = result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    # Check if truck belongs to ward (for ward admin)
    if current_user.role == "ward_admin" and truck.ward_id_assigned != current_user.ward_id:
        raise HTTPException(status_code=403, detail="Not authorized for this truck")
    
    # Update truck state
    truck.state = TruckState.DISPATCHED
    truck.ward_id_assigned = request.ward_id
    
    # Create truck task
    task = TruckTask(
        truck_id=truck_id,
        ward_id=request.ward_id,
        alert_id=request.alert_id,
        state=TaskState.DISPATCHED,
        dispatched_at=datetime.utcnow()
    )
    db.add(task)
    await db.commit()
    
    # Broadcast truck update
    await manager.broadcast({
        "type": "truck_update",
        "data": {
            "truck_id": truck_id,
            "state": "dispatched",
            "ward_id": request.ward_id
        }
    })
    
    return {"message": "Truck dispatched successfully"}


@app.post("/api/v1/trucks/{truck_id}/update_state")
async def update_truck_state(
    truck_id: int,
    request: TruckStateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck = result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    # Check ward access
    if not check_ward_access(current_user, truck.ward_id_assigned or 0):
        raise HTTPException(status_code=403, detail="Not authorized for this truck")
    
    truck.state = request.state
    await db.commit()
    
    # Broadcast truck update
    await manager.broadcast({
        "type": "truck_update",
        "data": {
            "truck_id": truck_id,
            "state": request.state.value
        }
    })
    
    return {"message": "Truck state updated successfully"}


@app.get("/api/v1/alerts", response_model=List[AlertResponse])
async def get_alerts(
    ward_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert)
    
    if current_user.role == "ward_admin":
        query = query.where(Alert.ward_id == current_user.ward_id)
    elif current_user.role == "user":
        query = query.where(Alert.ward_id == current_user.ward_id)
    elif ward_id:
        query = query.where(Alert.ward_id == ward_id)
    
    result = await db.execute(query.order_by(Alert.created_at.desc()))
    alerts = result.scalars().all()
    
    return [
        {
            "id": alert.id,
            "ward_id": alert.ward_id,
            "detection_id": alert.detection_id,
            "severity": alert.severity,
            "is_acknowledged": alert.is_acknowledged,
            "created_at": alert.created_at
        }
        for alert in alerts
    ]


@app.get("/api/v1/analytics/ward/{ward_id}")
async def get_ward_analytics(
    ward_id: int,
    range: str = "7d",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check ward access
    if not check_ward_access(current_user, ward_id):
        raise HTTPException(status_code=403, detail="Not authorized for this ward")
    
    # Simple analytics - count detections by label
    result = await db.execute(
        select(
            func.date(DetectionRecord.timestamp).label('date'),
            DetectionRecord.label,
            func.count(DetectionRecord.id).label('count')
        )
        .where(DetectionRecord.ward_id == ward_id)
        .group_by(func.date(DetectionRecord.timestamp), DetectionRecord.label)
        .order_by(func.date(DetectionRecord.timestamp))
    )
    
    analytics = result.all()
    
    # Format response
    response = []
    for date, label, count in analytics:
        response.append({
            "ward_id": ward_id,
            "date": str(date),
            "degradable_count": count if label == "degradable" else 0,
            "non_degradable_count": count if label == "non_degradable" else 0
        })
    
    return response


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket, token: Optional[str] = None):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or handle client messages
            await websocket.send_json({"type": "ping", "data": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
async def health():
    """Healthcheck endpoint (root-level, used by probes/healthchecks)."""
    return {"status": "healthy"}


@app.get("/api/v1/health")
async def health_v1():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
