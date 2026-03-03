"""Веб-авторизация: логин по login+пароль, JWT, проверка ролей."""
from collections import defaultdict, deque
from time import monotonic
from typing import Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.core.permissions import allowed_pavilions, get_menu_items
from app.config import settings
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


_failed_logins: Dict[str, Deque[float]] = defaultdict(deque)


def _is_rate_limited(key: str) -> bool:
    now = monotonic()
    window = settings.login_rate_limit_window_seconds
    max_attempts = settings.login_rate_limit_attempts
    attempts = _failed_logins[key]
    while attempts and (now - attempts[0]) > window:
        attempts.popleft()
    return len(attempts) >= max_attempts


def _register_failed_login(key: str) -> None:
    _failed_logins[key].append(monotonic())


def _clear_failed_logins(key: str) -> None:
    if key in _failed_logins:
        _failed_logins.pop(key, None)


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
    sub = payload["sub"]
    return UserInfo(
        id=int(sub) if isinstance(sub, str) else sub,
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


RequireAnyAuth = require_roles([
    EmployeeRole.ROLE_OPERATOR,
    EmployeeRole.ROLE_MANAGER,
    EmployeeRole.ROLE_ADMIN,
    EmployeeRole.ROLE_PLATE_OPERATOR,
])
RequireFormAccess = require_roles([EmployeeRole.ROLE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN])
RequireOrdersListAccess = require_roles([EmployeeRole.ROLE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN, EmployeeRole.ROLE_PLATE_OPERATOR])
RequireAnalyticsAccess = require_roles([EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN])
RequirePlateAccess = require_roles([EmployeeRole.ROLE_PLATE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN])
RequireCashAccess = require_roles([EmployeeRole.ROLE_OPERATOR, EmployeeRole.ROLE_PLATE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN])
RequireAdmin = require_roles([EmployeeRole.ROLE_ADMIN])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    username = (form.username or "").strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{username or '_empty'}"
    if _is_rate_limited(limiter_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Повторите позже.",
        )
    if not username:
        _register_failed_login(limiter_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    result = await db.execute(
        select(Employee).where(
            func.lower(Employee.login) == username,
            Employee.is_active == True,
        )
    )
    emp = result.scalar_one_or_none()
    if not emp or not emp.password_hash:
        _register_failed_login(limiter_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    if not verify_password(form.password, emp.password_hash):
        _register_failed_login(limiter_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    _clear_failed_logins(limiter_key)
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


class MenuItem(BaseModel):
    id: str
    label: str
    href: str
    divider: Optional[bool] = None
    action: Optional[str] = None
    group: Optional[str] = None


class MeResponse(BaseModel):
    id: int
    name: str
    role: str
    login: str
    allowed_pavilions: List[int]
    menu_items: List[MenuItem]


@router.get("/me", response_model=MeResponse)
async def me(current_user: UserInfo = Depends(RequireAnyAuth)):
    """Текущий пользователь, разрешённые павильоны и пункты меню по роли."""
    pavilions = allowed_pavilions(current_user.role)
    menu = get_menu_items(current_user.role)
    return MeResponse(
        id=current_user.id,
        name=current_user.name,
        role=current_user.role,
        login=current_user.login,
        allowed_pavilions=pavilions,
        menu_items=[
            MenuItem(
                id=m.get("id", ""),
                label=m.get("label", ""),
                href=m.get("href", "#"),
                divider=m.get("divider"),
                action=m.get("action"),
                group=m.get("group"),
            )
            for m in menu
        ],
    )


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    body: ChangePasswordBody,
    current_user: UserInfo = Depends(RequireAnyAuth),
    db: AsyncSession = Depends(get_db),
):
    """Смена пароля текущего пользователя (требуется старый пароль)."""
    from app.services.auth_service import hash_password
    if not body.new_password or len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="Новый пароль должен быть не менее 4 символов")
    result = await db.execute(select(Employee).where(Employee.id == current_user.id))
    emp = result.scalar_one_or_none()
    if not emp or not emp.password_hash:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not verify_password(body.old_password, emp.password_hash):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    emp.password_hash = hash_password(body.new_password)
    db.add(emp)
    await db.flush()
    return {"ok": True}
