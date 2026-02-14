"""
Бот павильона 2: получает callback от кнопок (Изготовлен / Доплата / Проблема)
и вызывает API backend для смены статуса заказа.
Запуск: TELEGRAM_BOT_TOKEN_PLATE=... API_BASE_URL=http://localhost:8000 python main.py
"""
import logging
import re

import httpx
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import API_BASE_URL, TELEGRAM_BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CALLBACK_PATTERN = re.compile(r"^plate:(\d+):(\w+)$")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not query.data:
        return
    m = CALLBACK_PATTERN.match(query.data)
    if not m:
        return
    order_id, status = m.group(1), m.group(2)
    telegram_id = update.effective_user.id if update.effective_user else None
    if not telegram_id:
        await query.edit_message_text(text=query.message.text + "\n\n❌ Ошибка: не удалось определить пользователя.")
        return
    url = f"{API_BASE_URL}/orders/{order_id}/status"
    headers = {"Content-Type": "application/json", "X-Telegram-User-Id": str(telegram_id)}
    payload = {"status": status}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.patch(url, json=payload, headers=headers, timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            await query.edit_message_text(
                text=query.message.text + f"\n\n✅ Статус обновлён: {data.get('status', status)}"
            )
        else:
            err = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
            await query.edit_message_text(text=query.message.text + f"\n\n❌ Ошибка: {err}")
    except Exception as e:
        logger.exception("Ошибка вызова API: %s", e)
        await query.edit_message_text(text=query.message.text + "\n\n❌ Ошибка связи с сервером.")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Задайте TELEGRAM_BOT_TOKEN_PLATE в окружении")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Бот павильона 2 запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
