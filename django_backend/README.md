# Django-подсистема (внутренний контур Document/Payment)

Использует ту же PostgreSQL, что и FastAPI. Таблицы: `django_documents`, `django_document_items`, `django_payments`.

## Установка и запуск

### 1. Установить зависимости

```bash
cd django_backend
pip install -r requirements.txt
```

(или использовать venv проекта: `..\.venv\Scripts\pip install -r requirements.txt`)

### 2. Настроить базу данных

Скопировать `../backend/.env` или задать переменную:

```
DATABASE_URL=postgresql://eye_user:eye_pass@localhost:5432/eye_w
```

(Если в backend используется `postgresql+asyncpg://`, Django сам подставит `postgresql://`.)

### 3. Применить миграции

```bash
python manage.py migrate
```

### 4. Запустить сервер (для теста)

```bash
python manage.py runserver 8001
```

API будет доступно на `http://localhost:8001/django/documents/`.

## Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /django/documents/ | Создать документ (тело как OrderCreate) |
| POST | /django/documents/{id}/payments/ | Добавить платёж `{amount, type}` |
| GET | /django/documents/{id}/ | Сводка документа, платежи, долг |

## Интеграция с nginx (опционально)

Чтобы проксировать `/django/` на Django:

```nginx
location /django/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

И запускать Django через systemd (отдельный сервис `eye_w_django`) на порту 8001.
