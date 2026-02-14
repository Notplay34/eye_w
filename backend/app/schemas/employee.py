from typing import Optional

from pydantic import BaseModel

from app.models import EmployeeRole


class EmployeeResponse(BaseModel):
    id: int
    name: str
    role: str
    telegram_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    name: str
    role: EmployeeRole
    telegram_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[EmployeeRole] = None
    telegram_id: Optional[int] = None
    is_active: Optional[bool] = None
