"""Схемы для касс и смен."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ShiftOpen(BaseModel):
    """Открыть смену."""
    pavilion: int = Field(..., ge=1, le=2, description="1 — павильон документов, 2 — павильон номеров")
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)


class ShiftClose(BaseModel):
    """Закрыть смену."""
    closing_balance: Decimal = Field(..., ge=0)


class ShiftResponse(BaseModel):
    id: int
    pavilion: int
    opened_by_id: int
    opened_at: str
    closed_at: Optional[str] = None
    closed_by_id: Optional[int] = None
    opening_balance: Decimal
    closing_balance: Optional[Decimal] = None
    status: str

    class Config:
        from_attributes = True


class ShiftCurrentResponse(BaseModel):
    """Текущая открытая смена + сумма по ней."""
    shift: ShiftResponse
    total_in_shift: Decimal
    """Сумма всех платежей за смену."""
