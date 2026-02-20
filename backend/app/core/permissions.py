"""
RBAC: роль × ресурс × павильон.
Ресурсы — типы данных/действий. Павильон 1 = документы/форма, 2 = номера/склад.
"""
from enum import Enum
from typing import List, Optional

from app.models.employee import EmployeeRole


class Resource(str, Enum):
    """Ресурсы для проверки доступа."""
    FORM_P1 = "FORM_P1"           # форма документов, заказы павильона 1
    PLATES_P2 = "PLATES_P2"       # изготовление номеров, заказы с need_plate
    CASH_P1 = "CASH_P1"           # касса павильона 1
    CASH_P2 = "CASH_P2"           # касса номеров (павильон 2)
    WAREHOUSE = "WAREHOUSE"       # склад заготовок
    ANALYTICS = "ANALYTICS"       # отчёты
    FINANCE = "FINANCE"           # финансы (сводки)
    USERS = "USERS"               # управление пользователями
    SETTINGS = "SETTINGS"         # системные настройки
    AUDIT = "AUDIT"               # история изменений
    SWITCH_PAVILION = "SWITCH_PAVILION"  # переключение павильона


# Павильоны, доступные роли (1 = документы, 2 = номера)
PAVILIONS_BY_ROLE = {
    EmployeeRole.ROLE_ADMIN: [1, 2],
    EmployeeRole.ROLE_MANAGER: [1, 2],
    EmployeeRole.ROLE_OPERATOR: [1],
    EmployeeRole.ROLE_PLATE_OPERATOR: [2],
}

# Ресурс → роли, которым разрешён доступ
RESOURCE_ROLES = {
    Resource.FORM_P1: [EmployeeRole.ROLE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
    Resource.PLATES_P2: [EmployeeRole.ROLE_PLATE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
    Resource.CASH_P1: [EmployeeRole.ROLE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
    Resource.CASH_P2: [EmployeeRole.ROLE_PLATE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
    Resource.WAREHOUSE: [EmployeeRole.ROLE_PLATE_OPERATOR, EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
    Resource.ANALYTICS: [EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
    Resource.FINANCE: [EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
    Resource.USERS: [EmployeeRole.ROLE_ADMIN],
    Resource.SETTINGS: [EmployeeRole.ROLE_ADMIN],
    Resource.AUDIT: [EmployeeRole.ROLE_ADMIN],
    Resource.SWITCH_PAVILION: [EmployeeRole.ROLE_MANAGER, EmployeeRole.ROLE_ADMIN],
}


def _parse_role(role: str) -> Optional[EmployeeRole]:
    try:
        return EmployeeRole(role)
    except ValueError:
        return None


def allowed_pavilions(role: str) -> List[int]:
    """Список павильонов (1, 2), доступных роли."""
    r = _parse_role(role)
    if r is None:
        return []
    return list(PAVILIONS_BY_ROLE.get(r, []))


def can_access_pavilion(role: str, pavilion: int) -> bool:
    """Проверка: может ли роль работать с данным павильоном."""
    return pavilion in allowed_pavilions(role)


def can_access_resource(role: str, resource: Resource) -> bool:
    """Проверка: есть ли у роли доступ к ресурсу."""
    r = _parse_role(role)
    if r is None:
        return False
    return r in RESOURCE_ROLES.get(resource, [])


def can_manage_users(role: str) -> bool:
    return can_access_resource(role, Resource.USERS)


def get_menu_items(role: str) -> List[dict]:
    """
    Пункты меню для роли. Каждый пункт: id, label, href, (опционально) divider.
    Фронт рендерит по этому списку.
    """
    r = _parse_role(role)
    if r is None:
        return []

    items = []
    # Все роли: ссылка на полное меню (страница с боковой панелью)
    items.append({"id": "menu", "label": "Меню", "href": "account.html"})

    if r == EmployeeRole.ROLE_ADMIN:
        items.extend([
            {"id": "users", "label": "Управление пользователями", "href": "users.html"},
            {"id": "settings", "label": "Настройки", "href": "admin.html"},
            {"id": "analytics", "label": "Отчёты", "href": "admin.html#analytics"},
            {"id": "finance", "label": "Финансы", "href": "cash-shifts.html"},
            {"id": "audit", "label": "История изменений", "href": "admin.html"},
            {"id": "div1", "label": "", "divider": True},
        ])
    elif r == EmployeeRole.ROLE_MANAGER:
        items.extend([
            {"id": "analytics", "label": "Отчёты", "href": "admin.html#analytics"},
            {"id": "finance", "label": "Финансы", "href": "cash-shifts.html"},
            {"id": "div1", "label": "", "divider": True},
        ])

    # Общие для всех авторизованных
    items.extend([
        {"id": "password", "label": "Сменить пароль", "href": "#", "action": "change_password"},
        {"id": "logout", "label": "Выйти", "href": "login.html", "action": "logout"},
    ])
    return items
