"""API касс и смен: открытие/закрытие смены по павильонам."""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.api.auth import RequireCashAccess, UserInfo
from app.models import CashShift, ShiftStatus, Payment, CashRow
from app.models.employee import EmployeeRole
from app.schemas.cash import (
    ShiftOpen, ShiftClose, ShiftResponse, ShiftCurrentResponse,
    CashRowCreate, CashRowUpdate, CashRowResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/cash", tags=["cash"])


def _shift_to_response(shift: CashShift) -> dict:
    return {
        "id": shift.id,
        "pavilion": shift.pavilion,
        "opened_by_id": shift.opened_by_id,
        "opened_at": shift.opened_at.isoformat() if shift.opened_at else "",
        "closed_at": shift.closed_at.isoformat() if shift.closed_at else None,
        "closed_by_id": shift.closed_by_id,
        "opening_balance": float(shift.opening_balance),
        "closing_balance": float(shift.closing_balance) if shift.closing_balance is not None else None,
        "status": shift.status.value,
    }


async def _get_current_shift(db: AsyncSession, pavilion: int) -> Optional[CashShift]:
    q = select(CashShift).where(
        CashShift.pavilion == pavilion,
        CashShift.status == ShiftStatus.OPEN,
    ).order_by(CashShift.opened_at.desc()).limit(1)
    r = await db.execute(q)
    return r.scalar_one_or_none()


def _can_manage_pavilion(user: UserInfo, pavilion: int) -> bool:
    try:
        role = EmployeeRole(user.role)
    except ValueError:
        return False
    if pavilion == 1:
        return role in (EmployeeRole.ROLE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN)
    return role in (EmployeeRole.ROLE_PLATE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN)


@router.post("/shifts", response_model=dict)
async def open_shift(
    body: ShiftOpen,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireCashAccess),
):
    """Открыть смену по павильону. Павильон 1 — оператор/менеджер/админ, павильон 2 — оператор изготовления/менеджер/админ."""
    if not _can_manage_pavilion(user, body.pavilion):
        raise HTTPException(status_code=403, detail="Нет доступа к кассе этого павильона")
    current = await _get_current_shift(db, body.pavilion)
    if current:
        raise HTTPException(
            status_code=400,
            detail=f"Смена павильона {body.pavilion} уже открыта (id={current.id}). Сначала закройте её.",
        )
    shift = CashShift(
        pavilion=body.pavilion,
        opened_by_id=user.id,
        opening_balance=body.opening_balance,
        status=ShiftStatus.OPEN,
    )
    db.add(shift)
    await db.flush()
    logger.info("Открыта смена id=%s павильон=%s", shift.id, body.pavilion)
    return {"id": shift.id, "pavilion": shift.pavilion, "opened_at": shift.opened_at.isoformat(), "status": "OPEN"}


@router.get("/shifts/current")
async def get_current_shift(
    pavilion: int = Query(..., ge=1, le=2),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireCashAccess),
):
    """Текущая открытая смена по павильону и сумма по ней."""
    if not _can_manage_pavilion(user, pavilion):
        raise HTTPException(status_code=403, detail="Нет доступа к кассе этого павильона")
    shift = await _get_current_shift(db, pavilion)
    if not shift:
        return {"shift": None, "total_in_shift": 0}
    q = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.shift_id == shift.id)
    r = await db.execute(q)
    total = r.scalar_one() or Decimal("0")
    return {
        "shift": _shift_to_response(shift),
        "total_in_shift": float(total),
    }


@router.get("/shifts", response_model=list)
async def list_shifts(
    pavilion: Optional[int] = Query(None, ge=1, le=2),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireCashAccess),
):
    """Список смен (фильтр по павильону и статусу)."""
    q = select(CashShift).order_by(CashShift.opened_at.desc()).limit(limit)
    if pavilion is not None:
        q = q.where(CashShift.pavilion == pavilion)
    if status is not None:
        try:
            q = q.where(CashShift.status == ShiftStatus(status))
        except ValueError:
            pass
    r = await db.execute(q)
    shifts = r.scalars().all()
    return [_shift_to_response(s) for s in shifts]


@router.patch("/shifts/{shift_id}/close", response_model=dict)
async def close_shift(
  shift_id: int,
  body: ShiftClose,
  db: AsyncSession = Depends(get_db),
  user: UserInfo = Depends(RequireCashAccess),
):
    """Закрыть смену (указать посчитанную наличность)."""
    r = await db.execute(select(CashShift).where(CashShift.id == shift_id))
    shift = r.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Смена не найдена")
    if shift.status != ShiftStatus.OPEN:
        raise HTTPException(status_code=400, detail="Смена уже закрыта")
    if not _can_manage_pavilion(user, shift.pavilion):
        raise HTTPException(status_code=403, detail="Нет доступа к кассе этого павильона")
    from datetime import datetime
    shift.closed_at = datetime.utcnow()
    shift.closed_by_id = user.id
    shift.closing_balance = body.closing_balance
    shift.status = ShiftStatus.CLOSED
    db.add(shift)
    await db.flush()
    logger.info("Закрыта смена id=%s павильон=%s", shift.id, shift.pavilion)
    return _shift_to_response(shift)


# --- Таблица кассы (редактируемые строки: ФИО, заявление, госпошлина, ДКП, страховка, номера, итого) ---

def _cash_row_to_dict(row: CashRow) -> dict:
    return {
        "id": row.id,
        "client_name": row.client_name or "",
        "application": float(row.application),
        "state_duty": float(row.state_duty),
        "dkp": float(row.dkp),
        "insurance": float(row.insurance),
        "plates": float(row.plates),
        "total": float(row.total),
    }


@router.get("/rows", response_model=list)
async def list_cash_rows(
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireCashAccess),
):
    """Список строк таблицы кассы (последние сверху)."""
    q = select(CashRow).order_by(CashRow.id.desc()).limit(limit)
    r = await db.execute(q)
    rows = r.scalars().all()
    return [_cash_row_to_dict(row) for row in rows]


@router.post("/rows", response_model=dict)
async def create_cash_row(
    body: CashRowCreate,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireCashAccess),
):
    """Добавить строку в таблицу кассы."""
    row = CashRow(
        client_name=body.client_name or "",
        application=body.application,
        state_duty=body.state_duty,
        dkp=body.dkp,
        insurance=body.insurance,
        plates=body.plates,
        total=body.total,
    )
    db.add(row)
    await db.flush()
    return _cash_row_to_dict(row)


@router.patch("/rows/{row_id}", response_model=dict)
async def update_cash_row(
    row_id: int,
    body: CashRowUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireCashAccess),
):
    """Обновить ячейки строки кассы (передавать только изменённые поля)."""
    r = await db.execute(select(CashRow).where(CashRow.id == row_id))
    row = r.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Строка не найдена")
    if body.client_name is not None:
        row.client_name = body.client_name
    if body.application is not None:
        row.application = body.application
    if body.state_duty is not None:
        row.state_duty = body.state_duty
    if body.dkp is not None:
        row.dkp = body.dkp
    if body.insurance is not None:
        row.insurance = body.insurance
    if body.plates is not None:
        row.plates = body.plates
    if body.total is not None:
        row.total = body.total
    db.add(row)
    await db.flush()
    return _cash_row_to_dict(row)


@router.delete("/rows/{row_id}", status_code=204)
async def delete_cash_row(
    row_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireCashAccess),
):
    """Удалить строку из таблицы кассы."""
    r = await db.execute(select(CashRow).where(CashRow.id == row_id))
    row = r.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Строка не найдена")
    await db.delete(row)
    await db.flush()
