"""Records both portals act on: vehicles, programs and reports."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_ward_access
from app.database import get_db
from app.models import Portal, Program, Report, User, Vehicle
from app.routers.ward import announce_program
from app.serializers import kmc_program, kmc_report, vehicle_out
from app.services import KMC_SCOPE, notify, ward_scope

router = APIRouter(prefix="/api/v1", tags=["shared"])


class VehiclePatch(BaseModel):
    driver: str | None = None
    status: str | None = None
    note: str | None = None


class Decision(BaseModel):
    approve: bool


class Attendance(BaseModel):
    attended: int = Field(ge=0)


class Registration(BaseModel):
    count: int = Field(default=1, ge=1)


class ReportPatch(BaseModel):
    status: str | None = Field(default=None, pattern="^(Pending|In Progress|Resolved)$")
    note: str | None = None


async def get_vehicle(db: AsyncSession, vehicle_id: str, user: User) -> Vehicle:
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    if user.portal != Portal.KMC and vehicle.ward != user.ward:
        raise HTTPException(status_code=403, detail="Not authorized for this vehicle")
    return vehicle


async def get_program(db: AsyncSession, program_id: int, user: User) -> Program:
    program = await db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    require_ward_access(user, program.ward)
    return program


@router.patch("/vehicles/{vehicle_id}")
async def patch_vehicle(vehicle_id: str, body: VehiclePatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vehicle = await get_vehicle(db, vehicle_id, user)
    for field in ("driver", "status", "note"):
        if (value := getattr(body, field)) is not None:
            setattr(vehicle, field, value)
    await db.commit()
    return vehicle_out(vehicle)


@router.post("/programs/{program_id}/decision")
async def decide_program(program_id: int, body: Decision, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """KMC's review of a ward program. The ward portal also calls this to simulate KMC's answer."""
    program = await get_program(db, program_id, user)
    program.approval = "Approved" if body.approve else "Needs changes"
    if body.approve:
        program.status = "Upcoming"
        announce_program(db, program)
    notify(db, ward_scope(program.ward), f"KMC {'approved' if body.approve else 'requested changes to'} \"{program.name}\"", "/ward/awareness")
    await db.commit()
    return kmc_program(program)


@router.post("/programs/{program_id}/resubmit")
async def resubmit_program(program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    program = await get_program(db, program_id, user)
    program.approval = "Pending KMC review"
    notify(db, KMC_SCOPE, f"Ward {program.ward} resubmitted \"{program.name}\" for review", "/kmc/awareness")
    await db.commit()
    return kmc_program(program)


@router.post("/programs/{program_id}/start")
async def start_program(program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    program = await get_program(db, program_id, user)
    program.status = "Running"
    await db.commit()
    return kmc_program(program)


@router.post("/programs/{program_id}/complete")
async def complete_program(program_id: int, body: Attendance, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    program = await get_program(db, program_id, user)
    program.status, program.attended = "Completed", body.attended
    notify(db, KMC_SCOPE, f"\"{program.name}\" completed in Ward {program.ward} ({body.attended} attended)", "/kmc/awareness")
    await db.commit()
    return kmc_program(program)


@router.post("/programs/{program_id}/register")
async def register_citizens(program_id: int, body: Registration, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    program = await get_program(db, program_id, user)
    program.registered += body.count
    await db.commit()
    return kmc_program(program)


@router.patch("/reports/{report_id}")
async def patch_report(report_id: int, body: ReportPatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    require_ward_access(user, report.ward)
    if body.status is not None:
        report.status = body.status
    if body.note:
        report.notes = [*(report.notes or []), body.note]
    await db.commit()
    return kmc_report(report)
