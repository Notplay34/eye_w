"""Проверка роли по telegram_id для ботов."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Employee
from app.models.employee import EmployeeRole

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/check-admin")
async def check_admin(
    telegram_id: int = Query(..., description="Telegram user id"),
    db: AsyncSession = Depends(get_db),
):
    """Возвращает is_admin: true, если пользователь есть в employees с role=ROLE_ADMIN."""
    r = await db.execute(
        select(Employee.id).where(
            Employee.telegram_id == telegram_id,
            Employee.role == EmployeeRole.ROLE_ADMIN,
            Employee.is_active == True,
        )
    )
    return {"is_admin": r.scalar_one_or_none() is not None}
