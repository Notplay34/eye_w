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
| POST | /employees | Создание сотрудника |
| PATCH | /employees/{id} | Обновление сотрудника (имя, роль, telegram_id, is_active) |
| GET | /analytics/today | Сводка за день |
| GET | /analytics/month | Сводка за месяц |
| GET | /analytics/employees | Учёт по сотрудникам |

---

## Telegram-боты

### Бот павильона 2 (изготовление номеров)

- При оплате заказа с номером операторы павильона 2 получают уведомление в Telegram (кто в `employees` с ролью `ROLE_PLATE_OPERATOR` и заполненным `telegram_id`).
- Отдельный процесс обрабатывает нажатия кнопок «Изготовлен», «Доплата получена», «Проблема» и вызывает API для смены статуса заказа.

Запуск:

```bash
cd bot_plate
pip install -r requirements.txt
set TELEGRAM_BOT_TOKEN_PLATE=токен_бота
set API_BASE_URL=http://localhost:8000
python main.py
```

В backend задать переменную `TELEGRAM_BOT_TOKEN_PLATE` (тот же токен) для отправки уведомлений при оплате.

### Бот владельца (аналитика)

- Команды: `/today`, `/month`, `/employees`.
- Доступ только для пользователей, у которых `telegram_id` записан в `employees` с ролью `ROLE_ADMIN`.

Запуск:

```bash
cd bot_owner
pip install -r requirements.txt
set TELEGRAM_BOT_TOKEN_OWNER=токен_бота_владельца
set API_BASE_URL=http://localhost:8000
python main.py
```

В БД у владельца должен быть заполнен `telegram_id` (узнать свой id можно через @userinfobot).

---

## Как тестировать

1. **База данных.** Должен быть запущен PostgreSQL с БД `eye_w`.
   - Локально: создать БД и пользователя, в `backend/.env` указать `DATABASE_URL`.
   - Через Docker (если установлен): в корне проекта выполнить `docker compose up -d` — поднимется PostgreSQL (порт 5432, пользователь `eye_user`, пароль `eye_pass`, БД `eye_w`). В `backend/.env` задать:
     ```
     DATABASE_URL=postgresql+asyncpg://eye_user:eye_pass@localhost:5432/eye_w
     ```

2. **Backend:** из корня проекта:
   ```bash
   .venv\Scripts\activate
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Проверка: http://localhost:8000/docs и http://localhost:8000/health

3. **Frontend:** в другом терминале:
   ```bash
   cd frontend
   python -m http.server 8080
   ```
   Открыть http://localhost:8080 — форма оператора. Создать через API или форму заказ, принять оплату, проверить аналитику и скачивание документов.

4. **Сотрудники:** через Swagger (POST /employees) создать сотрудника; PATCH /employees/{id} — обновить (например, указать telegram_id для ботов).

---

## Дальнейшая разработка

- При необходимости: авторизация в веб-интерфейсе, миграции БД (Alembic)

См. **DEVELOPMENT_PLAN.md** и **DEVELOPMENT_LOG.md**.
