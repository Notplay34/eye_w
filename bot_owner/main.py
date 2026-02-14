"""
Бот владельца: /today, /month, /employees.
Доступ только для пользователей, чей telegram_id записан в employees с role=ROLE_ADMIN.
Запуск: TELEGRAM_BOT_TOKEN_OWNER=... API_BASE_URL=http://localhost:8000 python main.py
"""
import logging
from decimal import Decimal

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import API_BASE_URL, TELEGRAM_BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _require_admin(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return False
    # Проверка через API
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{API_BASE_URL}/auth/check-admin",
                params={"telegram_id": user_id},
                timeout=10.0,
            )
        if r.status_code == 200 and (r.json() or {}).get("is_admin"):
            return True
    except Exception as e:
        logger.warning("check-admin: %s", e)
    if update.message:
        await update.message.reply_text("Доступ только для владельца.")
    return False


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update):
        return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{API_BASE_URL}/analytics/today", timeout=10.0)
        if r.status_code != 200:
            await update.message.reply_text("Ошибка API.")
            return
        d = r.json()
        total = Decimal(str(d.get("total_revenue", 0)))
        duty = Decimal(str(d.get("state_duty_total", 0)))
        cnt = d.get("orders_count", 0)
        avg = Decimal(str(d.get("average_cheque", 0)))
        text = (
            f"📊 За сегодня\n\n"
            f"Выручка: {total} ₽\n"
            f"Госпошлина: {duty} ₽\n"
            f"Заказов: {cnt}\n"
            f"Средний чек: {avg} ₽"
        )
        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("today: %s", e)
        await update.message.reply_text("Ошибка запроса.")


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update):
        return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{API_BASE_URL}/analytics/month", timeout=10.0)
        if r.status_code != 200:
            await update.message.reply_text("Ошибка API.")
            return
        d = r.json()
        total = Decimal(str(d.get("total_revenue", 0)))
        duty = Decimal(str(d.get("state_duty_total", 0)))
        cnt = d.get("orders_count", 0)
        avg = Decimal(str(d.get("average_cheque", 0)))
        text = (
            f"📊 За месяц\n\n"
            f"Выручка: {total} ₽\n"
            f"Госпошлина: {duty} ₽\n"
            f"Заказов: {cnt}\n"
            f"Средний чек: {avg} ₽"
        )
        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("month: %s", e)
        await update.message.reply_text("Ошибка запроса.")


async def cmd_employees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update):
        return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{API_BASE_URL}/analytics/employees",
                params={"period": "month"},
                timeout=10.0,
            )
        if r.status_code != 200:
            await update.message.reply_text("Ошибка API.")
            return
        d = r.json()
        lines = ["👥 Учёт по сотрудникам (месяц)\n"]
        for emp in d.get("employees", []):
            lines.append(
                f"{emp.get('employee_name', '—')}: "
                f"{emp.get('orders_count', 0)} заказов, "
                f"{emp.get('total_amount', 0)} ₽"
            )
        await update.message.reply_text("\n".join(lines) if len(lines) > 1 else "Нет данных.")
    except Exception as e:
        logger.exception("employees: %s", e)
        await update.message.reply_text("Ошибка запроса.")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Задайте TELEGRAM_BOT_TOKEN_OWNER в окружении")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("month", cmd_month))
    app.add_handler(CommandHandler("employees", cmd_employees))
    logger.info("Бот владельца запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
