# Развёртывание на сервере (Linux)

Краткий порядок действий после SSH-подключения к серверу (например `ssh root@194.87.103.157`).

**Вход в систему:** При первом запуске создаётся суперпользователь **sergey151** / **1wq21wq2** (директор). Остальных сотрудников добавляет директор в разделе «Управление аккаунтами».

**Чтобы всё запустилось одной командой** (после того как установлены PostgreSQL, nginx, код в `/opt/eye_w`, backend установлен в venv и настроен systemd-сервис `eye_w`):

```bash
cd /opt/eye_w && git pull && bash deploy/setup_server.sh
```

Скрипт добавит `JWT_SECRET` в `backend/.env` (если нет), подставит nginx-конфиг с поддержкой входа и перезапустит сервисы. После этого откройте сайт и войдите: **sergey151** / **1wq21wq2**.

**Домен (DuckDNS и т.п.):** Чтобы открывать сайт по имени (например `eye34z.duckdns.org`): (1) В панели DuckDNS привязать домен к IP сервера. (2) При деплое задать `SERVER_NAME=eye34z.duckdns.org` перед запуском скрипта или после деплоя вручную в nginx в `server_name` указать этот домен и выполнить `nginx -t && systemctl reload nginx`. Frontend при открытии с этого домена сам ходит в API на тот же хост (прокси через nginx).

---

## 1. Подготовка системы

```bash
apt update && apt install -y python3.11 python3.11-venv python3-pip postgresql nginx git
```

(Для CentOS/Rocky: `dnf install python3.11 postgresql-server nginx git` и настройка PostgreSQL.)

---

## 2. PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER eye_user WITH PASSWORD 'eye_pass';"
sudo -u postgres psql -c "CREATE DATABASE eye_w OWNER eye_user;"
```

Пароль `eye_pass` лучше заменить на свой и использовать его в `backend/.env`.

---

## 3. Код проекта

**Вариант А — клонирование с GitHub:**

```bash
cd /opt
git clone https://github.com/Notplay34/eye_w.git
cd eye_w
```

**Вариант Б — загрузка с локальной машины (на Windows в PowerShell):**

```powershell
scp -r c:\dev\eye_w root@194.87.103.157:/opt/eye_w
```

Потом на сервере: `cd /opt/eye_w`.

---

## 4. Backend

```bash
cd /opt/eye_w/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Создать файл `.env`:

```bash
nano .env
```

Содержимое (подставьте свой пароль БД и при необходимости хост):

```
DATABASE_URL=postgresql+asyncpg://eye_user:eye_pass@localhost:5432/eye_w
JWT_SECRET=придумайте_длинный_секретный_ключ
```

Запуск вручную для проверки:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверка: `curl http://localhost:8000/health`. После проверки остановить (Ctrl+C) и запустить через systemd (шаг 6).

---

## 5. Frontend

Файлы уже в `frontend/`. Нужно, чтобы в браузере запросы шли на ваш API. В `frontend/app.js` задаётся `API_BASE_URL` — на сервере укажите туда публичный адрес API (например `https://api.ваш-домен.ru` или `http://IP:8000`), либо раздавайте frontend через тот же домен, что и API, и используйте относительные пути.

Раздача через nginx (шаг 6) — и статика `frontend/`, и прокси на backend.

---

## 6. Nginx и автозапуск backend

Готовый конфиг лежит в репозитории: `deploy/nginx-eye_w.conf`. Скопировать и включить:

```bash
cp /opt/eye_w/deploy/nginx-eye_w.conf /etc/nginx/sites-available/eye_w
ln -sf /etc/nginx/sites-available/eye_w /etc/nginx/sites-enabled/eye_w
nginx -t && systemctl reload nginx
```

Важно: в конфиге используется **location /auth/** (со слэшем), иначе запрос к файлу `auth.js` уйдёт в бэкенд и форма входа не заработает. Для работы входа во всех API-локациях должен быть **proxy_set_header Authorization $http_authorization;**.

**Systemd-сервис для backend** (`/etc/systemd/system/eye_w.service`):

```ini
[Unit]
Description=Eye-W Backend
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=/opt/eye_w/backend
ExecStart=/opt/eye_w/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable eye_w
systemctl start eye_w
systemctl status eye_w
```

---

## 7. Итог

- **Сайт с формой:** http://ваш-домен.ru (или http://IP).
- **API и здоровье:** http://ваш-домен.ru/health, http://ваш-домен.ru/docs.
- В `frontend/app.js` в `API_BASE_URL` указать тот же хост, чтобы запросы шли на ваш сервер.

После изменений кода: `git pull` (или заново загрузить файлы), перезапуск backend: `systemctl restart eye_w`.
