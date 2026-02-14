from pydantic import BaseModel

from app.models import EmployeeRole


class EmployeeResponse(BaseModel):
    id: int
    name: str
    role: str
    telegram_id: int | None
    is_active: bool

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    name: str
    role: EmployeeRole
    telegram_id: int | None = None
