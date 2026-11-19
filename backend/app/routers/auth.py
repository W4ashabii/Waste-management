from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user, get_password_hash, verify_password
from app.database import get_db
from app import sms
from app.models import Driver, Portal, User, Ward
from app.serializers import user_out

router = APIRouter(prefix="/api/v1", tags=["auth"])
PORTALS = f"^({Portal.KMC}|{Portal.WARD}|{Portal.CITIZEN}|{Portal.DRIVER})$"
PORTAL_NAMES = {
    Portal.KMC: "KMC staff portal", Portal.WARD: "ward staff portal", Portal.CITIZEN: "citizen section", Portal.DRIVER: "driver section",
}
FALLBACK_ROLES = {Portal.KMC: "KMC Staff", Portal.WARD: "Ward Staff", Portal.CITIZEN: "Resident", Portal.DRIVER: "Driver"}


class LoginRequest(BaseModel):
    email: str
    password: str
    portal: str = Field(pattern=PORTALS)


class SignupRequest(LoginRequest):
    name: str = Field(min_length=1)
    role: str = ""
    # Citizens choose their ward when they sign up; ward staff choose it after login.
    ward: int | None = None
    phone: str | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    role: str | None = None
    email: str | None = Field(default=None, min_length=3)
    ward: int | None = None
    phone: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


def token_response(user: User) -> dict:
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_out(user)}


async def email_taken(db: AsyncSession, email: str) -> bool:
    return (await db.execute(select(User.id).where(User.email == email))).first() is not None


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email.strip().lower()))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if user.portal != body.portal:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"This account is for the {PORTAL_NAMES[user.portal]}")
    return token_response(user)


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    if await email_taken(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    ward = None
    if body.portal == Portal.CITIZEN:
        if body.ward is None:
            raise HTTPException(status_code=422, detail="Choose your ward")
        if await db.get(Ward, body.ward) is None:
            raise HTTPException(status_code=404, detail=f"Ward {body.ward} not found")
        ward = body.ward
    phone = phone_or_422(body.phone) if body.phone else None
    name = body.name.strip()
    user = User(
        name=name, role=body.role.strip() or FALLBACK_ROLES[body.portal], email=email,
        password_hash=get_password_hash(body.password), portal=body.portal, ward=ward, phone=phone,
    )
    db.add(user)
    if body.portal == Portal.DRIVER and (await db.execute(select(Driver.id).where(Driver.name == name))).first() is None:
        db.add(Driver(name=name))  # so ward staff can assign the new driver to a vehicle
    await db.commit()
    await db.refresh(user)
    return token_response(user)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.patch("/me")
async def update_me(body: ProfileUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.name is not None:
        if user.portal == Portal.DRIVER and body.name.strip() != user.name:
            # Vehicles are assigned to drivers by name.
            raise HTTPException(status_code=400, detail="Ask your ward office to change a driver's name")
        user.name = body.name.strip()
    if body.role is not None:
        user.role = body.role.strip()
    if body.email is not None:
        email = body.email.strip().lower()
        if email != user.email and await email_taken(db, email):
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = email
    if body.ward is not None:
        # Ward staff pick the ward they manage after logging in; citizens can move ward.
        if user.portal not in (Portal.WARD, Portal.CITIZEN):
            raise HTTPException(status_code=400, detail="Only ward staff and citizens have a ward")
        if await db.get(Ward, body.ward) is None:
            raise HTTPException(status_code=404, detail=f"Ward {body.ward} not found")
        user.ward = body.ward
    if body.phone is not None:
        user.phone = phone_or_422(body.phone) if body.phone.strip() else None
    await db.commit()
    return user_out(user)


def phone_or_422(value: str) -> str:
    try:
        return sms.normalize_phone(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: PasswordChange, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = get_password_hash(body.new_password)
    await db.commit()
