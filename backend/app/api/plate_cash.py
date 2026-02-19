"""API кассы номеров: таблица Фамилия и Сумма (сумма может быть отрицательной)."""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.api.auth import RequirePlateAccess, UserInfo
from app.models import PlateCashRow

logger = get_logger(__name__)
router = APIRouter(prefix="/plate-cash", tags=["plate-cash"])


class PlateCashRowCreate(BaseModel):
    client_name: str = ""
    amount: float = 0


class PlateCashRowUpdate(BaseModel):
    client_name: Optional[str] = None
    amount: Optional[float] = None


def _row_to_dict(row: PlateCashRow) -> dict:
    return {
        "id": row.id,
        "client_name": row.client_name or "",
        "amount": float(row.amount),
    }


@router.get("/rows")
async def list_plate_cash_rows(
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequirePlateAccess),
):
    """Список строк кассы номеров (последние сверху)."""
    q = select(PlateCashRow).order_by(PlateCashRow.id.desc()).limit(limit)
    r = await db.execute(q)
    rows = r.scalars().all()
    total = sum(float(row.amount) for row in rows)
    return {
        "rows": [_row_to_dict(row) for row in rows],
        "total": total,
    }


@router.post("/rows")
async def create_plate_cash_row(
    body: PlateCashRowCreate,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequirePlateAccess),
):
    """Добавить строку (сумма может быть отрицательной — изъятие из кассы)."""
    row = PlateCashRow(
        client_name=(body.client_name or "").strip(),
        amount=Decimal(str(body.amount)),
    )
    db.add(row)
    await db.flush()
    return _row_to_dict(row)


@router.patch("/rows/{row_id}")
async def update_plate_cash_row(
    row_id: int,
    body: PlateCashRowUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequirePlateAccess),
):
    """Обновить ячейки строки."""
    r = await db.execute(select(PlateCashRow).where(PlateCashRow.id == row_id))
    row = r.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Строка не найдена")
    if body.client_name is not None:
        row.client_name = body.client_name.strip()
    if body.amount is not None:
        row.amount = Decimal(str(body.amount))
    db.add(row)
    await db.flush()
    return _row_to_dict(row)


@router.delete("/rows/{row_id}", status_code=204)
async def delete_plate_cash_row(
    row_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequirePlateAccess),
):
    """Удалить строку."""
    r = await db.execute(select(PlateCashRow).where(PlateCashRow.id == row_id))
    row = r.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Строка не найдена")
    await db.delete(row)
    await db.flush()
