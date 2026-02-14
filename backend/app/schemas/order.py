from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    """Данные формы оператора (раздел 13 PROJECT_CONTEXT)."""
    client_fio: Optional[str] = None
    client_passport: Optional[str] = None
    client_address: Optional[str] = None
    client_phone: Optional[str] = None
    client_comment: Optional[str] = None
    seller_fio: Optional[str] = None
    seller_passport: Optional[str] = None
    seller_address: Optional[str] = None
    vin: Optional[str] = None
    brand_model: Optional[str] = None
    vehicle_type: Optional[str] = None
    year: Optional[str] = None
    engine: Optional[str] = None
    chassis: Optional[str] = None
    body: Optional[str] = None
    color: Optional[str] = None
    srts: Optional[str] = None
    plate_number: Optional[str] = None
    pts: Optional[str] = None
    service_type: Optional[str] = None
    need_plate: bool = False
    state_duty: Decimal = Field(default=Decimal("0"), ge=0)
    extra_amount: Decimal = Field(default=Decimal("0"), ge=0)
    plate_amount: Decimal = Field(default=Decimal("0"), ge=0)
    summa_dkp: Decimal = Field(default=Decimal("0"), ge=0)
    employee_id: Optional[int] = None


class OrderResponse(BaseModel):
    id: int
    public_id: str
    status: str
    total_amount: Decimal
    state_duty_amount: Decimal
    income_pavilion1: Decimal
    income_pavilion2: Decimal
    need_plate: bool
    service_type: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True
