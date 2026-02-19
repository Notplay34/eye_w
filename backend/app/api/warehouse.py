"""Склад заготовок номеров: остатки, пополнение, резерв, списание."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import RequirePlateAccess, UserInfo
from app.core.database import get_db
from app.models import PlateStock, PlateReservation

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


async def _get_or_create_stock(db: AsyncSession) -> PlateStock:
    r = await db.execute(select(PlateStock).limit(1))
    row = r.scalar_one_or_none()
    if not row:
        row = PlateStock(quantity=0)
        db.add(row)
        await db.flush()
    return row


async def _reserved_total(db: AsyncSession) -> int:
    r = await db.execute(select(func.coalesce(func.sum(PlateReservation.quantity), 0)))
    return int(r.scalar_one() or 0)


@router.get("/plate-stock")
async def get_plate_stock(
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequirePlateAccess),
):
    """Текущий остаток и зарезервировано."""
    stock = await _get_or_create_stock(db)
    reserved = await _reserved_total(db)
    return {
        "quantity": stock.quantity,
        "reserved": reserved,
        "available": max(0, stock.quantity - reserved),
    }


class AddStockBody(BaseModel):
    amount: int


@router.post("/plate-stock/add")
async def add_plate_stock(
    body: AddStockBody,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequirePlateAccess),
):
    """Пополнить склад заготовок."""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть больше нуля")
    stock = await _get_or_create_stock(db)
    stock.quantity += body.amount
    db.add(stock)
    await db.flush()
    return {"quantity": stock.quantity, "added": body.amount}
