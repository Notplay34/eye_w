from decimal import Decimal
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    """Данные формы оператора (раздел 13 PROJECT_CONTEXT)."""
    client_fio: str | None = None
    client_passport: str | None = None
    client_address: str | None = None
    client_phone: str | None = None
    client_comment: str | None = None
    seller_fio: str | None = None
    seller_passport: str | None = None
    seller_address: str | None = None
    vin: str | None = None
    brand_model: str | None = None
    vehicle_type: str | None = None
    year: str | None = None
    engine: str | None = None
    chassis: str | None = None
    body: str | None = None
    color: str | None = None
    srts: str | None = None
    plate_number: str | None = None
    pts: str | None = None
    service_type: str | None = None
    need_plate: bool = False
    state_duty: Decimal = Field(default=Decimal("0"), ge=0)
    extra_amount: Decimal = Field(default=Decimal("0"), ge=0)
    plate_amount: Decimal = Field(default=Decimal("0"), ge=0)
    summa_dkp: Decimal = Field(default=Decimal("0"), ge=0)
    employee_id: int | None = None


class OrderResponse(BaseModel):
    id: int
    public_id: str
    status: str
    total_amount: Decimal
    state_duty_amount: Decimal
    income_pavilion1: Decimal
    income_pavilion2: Decimal
    need_plate: bool
    service_type: str | None
    created_at: str

    class Config:
        from_attributes = True
