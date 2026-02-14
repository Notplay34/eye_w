from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Employee
from app.schemas.employee import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeResponse])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Employee).where(Employee.is_active == True).order_by(Employee.id)
    )
    employees = result.scalars().all()
    return [
        EmployeeResponse(
            id=e.id,
            name=e.name,
            role=e.role.value,
            telegram_id=e.telegram_id,
            is_active=e.is_active,
        )
        for e in employees
    ]


@router.post("", response_model=EmployeeResponse)
async def create_employee(data: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    emp = Employee(
        name=data.name,
        role=data.role,
        telegram_id=data.telegram_id,
    )
    db.add(emp)
    await db.flush()
    await db.refresh(emp)
    return EmployeeResponse(
        id=emp.id,
        name=emp.name,
        role=emp.role.value,
        telegram_id=emp.telegram_id,
        is_active=emp.is_active,
    )
