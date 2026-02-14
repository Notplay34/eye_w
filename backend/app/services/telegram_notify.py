"""
Отправка уведомлений в Telegram при оплате заказа с номером.
Использует Telegram Bot API; список получателей — employees с role=ROLE_PLATE_OPERATOR.
"""
import os
from decimal import Decimal
from typing import Optional

import httpx

from app.core.logging_config import get_logger

logger = get_logger(__name__)

def _get_bot_token() -> Optional[str]:
    return os.environ.get("TELEGRAM_BOT_TOKEN_PLATE")


def _format_order_message(order_id: int, public_id: str, total: Decimal, plate_quantity: int = 1) -> str:
    qty = f", {plate_quantity} шт" if plate_quantity > 1 else ""
    return (
        f"🆕 Новый заказ с номером{qty}\n\n"
        f"ID: {public_id} (#{order_id})\n"
        f"Сумма: {total} ₽\n"
        f"Статус: Оплачен"
    )


async def get_plate_operator_chat_ids(db) -> list[int]:
    """Возвращает telegram_id сотрудников с ролью PLATE_OPERATOR."""
    from sqlalchemy import select
    from app.models import Employee
    from app.models.employee import EmployeeRole

    result = await db.execute(
        select(Employee.telegram_id).where(
            Employee.role == EmployeeRole.ROLE_PLATE_OPERATOR,
            Employee.telegram_id.isnot(None),
            Employee.is_active == True,
        )
    )
    rows = result.scalars().all()
    return [r for r in rows if r is not None]


async def notify_plate_operators_new_order(
    db, order_id: int, public_id: str, total: Decimal, plate_quantity: int = 1
) -> None:
    """Отправляет уведомление о новом заказе с номером всем операторам павильона 2."""
    token = _get_bot_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN_PLATE не задан — уведомление не отправлено")
        return
    chat_ids = await get_plate_operator_chat_ids(db)
    if not chat_ids:
        logger.warning("Нет операторов павильона 2 с telegram_id — уведомление не отправлено")
        return
    text = _format_order_message(order_id, public_id, total, plate_quantity)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "text": text,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "Изготовлен", "callback_data": f"plate:{order_id}:PLATE_READY"},
                    {"text": "Доплата получена", "callback_data": f"plate:{order_id}:PLATE_READY"},
                ],
                [{"text": "Проблема", "callback_data": f"plate:{order_id}:PROBLEM"}],
            ]
        },
    }
    async with httpx.AsyncClient() as client:
        for chat_id in chat_ids:
            try:
                r = await client.post(url, json={**payload, "chat_id": chat_id}, timeout=10.0)
                if r.status_code != 200:
                    logger.warning("Telegram sendMessage %s: %s", r.status_code, r.text)
            except Exception as e:
                logger.exception("Ошибка отправки в Telegram chat_id=%s: %s", chat_id, e)
