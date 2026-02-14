"""Веб-авторизация: логин по login+пароль, JWT, проверка ролей. Для ботов — check-admin по telegram_id."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models import Employee
from app.models.employee import EmployeeRole
from app.services.auth_service import (
    create_access_token,
    decode_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


class UserInfo(BaseModel):
    id: int
    name: str
    role: str
    login: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserInfo]:
    has_header = credentials is not None and credentials.scheme.lower() == "bearer"
    if not has_header:
        logger.warning("auth/me: заголовок Authorization отсутствует или не Bearer")
        return None
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        logger.warning("auth/me: токен не прошёл проверку (неверный или истёк)")
        return None
    return UserInfo(
        id=payload["sub"],
        name=payload.get("name", ""),
        role=payload.get("role", ""),
        login=payload.get("login", ""),
    )


def require_roles(allowed_roles: List[EmployeeRole]):
    async def _check(
        current_user: Optional[UserInfo] = Depends(get_current_user),
    ) -> UserInfo:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется авторизация",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            role_enum = EmployeeRole(current_user.role)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неизвестная роль")
        if role_enum not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return current_user
    return _check


RequireFormAccess = require_roles([EmployeeRole.ROLE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN])
RequireAnalyticsAccess = require_roles([EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN])
RequireAdmin = require_roles([EmployeeRole.ROLE_ADMIN])


@router.post("/login", response_model=LoginResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    username = (form.username or "").strip().lower()
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    result = await db.execute(
        select(Employee).where(
            func.lower(Employee.login) == username,
            Employee.is_active == True,
        )
    )
    emp = result.scalar_one_or_none()
    if not emp or not emp.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    if not verify_password(form.password, emp.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    token = create_access_token(
        subject=emp.id,
        role=emp.role.value,
        name=emp.name,
        login=emp.login or "",
    )
    return LoginResponse(
        access_token=token,
        user=UserInfo(id=emp.id, name=emp.name, role=emp.role.value, login=emp.login or ""),
    )


@router.get("/me", response_model=UserInfo)
async def me(current_user: UserInfo = Depends(RequireFormAccess)):
    return current_user


@router.get("/check-admin")
async def check_admin(
    telegram_id: int = Query(..., description="Telegram user id"),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(Employee.id).where(
            Employee.telegram_id == telegram_id,
            Employee.role == EmployeeRole.ROLE_ADMIN,
            Employee.is_active == True,
        )
    )
    return {"is_admin": r.scalar_one_or_none() is not None}
