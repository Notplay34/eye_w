# Павильоны МРЭО — система учёта и контроля

Система управления двумя павильонами автоуслуг: оформление документов, изготовление номеров, учёт платежей, аналитика. См. **PROJECT_CONTEXT.md** и **DEVELOPMENT_PLAN.md**.

---

## Требования

- Python 3.11+
- PostgreSQL
- (Опционально) Node или простой HTTP-сервер для frontend

---

## Backend (FastAPI)

1. Создать виртуальное окружение и установить зависимости:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. Настроить БД: скопировать `backend/.env.example` в `backend/.env` и задать `DATABASE_URL`:

   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/eye_w
   ```

3. Запуск:

   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Документация API: http://localhost:8000/docs

---

## Frontend (веб-форма операторов)

Статические файлы в папке **frontend/** (HTML, CSS, JS). Подключение к API по умолчанию: `http://localhost:8000`.

1. Открыть в браузере файл `frontend/index.html`  
   **или**
2. Запустить любой HTTP-сервер из папки `frontend`, например:

   ```bash
   cd frontend
   python -m http.server 8080
   ```
   Затем открыть http://localhost:8080

---

## Шаблоны документов

Папка **templates/** в корне проекта — шаблоны docx для генерации документов (DKP, МРЭО, заявления и т.д.). Backend подставляет данные заказа в плейсхолдеры `{{ ... }}`.

---

## Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /health | Проверка работы сервера |
| POST | /orders | Создание заказа |
| POST | /orders/{id}/pay | Принять оплату по заказу |
| GET | /orders | Список заказов |
| GET | /orders/{id} | Заказ по id |
| GET | /orders/{id}/documents/{template} | Скачать сгенерированный docx |
| GET | /employees | Список сотрудников |
| GET | /analytics/today | Сводка за день |
| GET | /analytics/month | Сводка за месяц |
| GET | /analytics/employees | Учёт по сотрудникам |

---

## Дальнейшая разработка

- Telegram-бот павильона 2 (уведомления, смена статусов)
- Telegram-бот владельца (/today, /month, /employees)
- При необходимости: авторизация, миграции БД (Alembic)

См. **DEVELOPMENT_PLAN.md** и **DEVELOPMENT_LOG.md**.
