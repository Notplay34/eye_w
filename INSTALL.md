# Как установить и запустить систему «Павильоны МРЭО»

**Для кого:** владелец или человек, который настраивает сервер.  
**Что получится:** рабочий сайт, куда заходят операторы и оформляют заказы.

---

## Вариант 1: Сервер уже настроен (только обновить код)

Если система уже стояла раньше и нужно просто подтянуть новую версию:

```bash
cd /opt/eye_w
git pull
bash deploy/setup_server.sh
```

Готово. Откройте сайт в браузере.

---

## Вариант 2: Чистый сервер с нуля

### Шаг 1. Подключиться к серверу

Через SSH, например:

```
ssh root@ВАШ_IP
```

(подставьте свой IP или домен)

---

### Шаг 2. Установить нужные программы

Скопируйте и выполните одну команду:

```bash
apt update && apt install -y python3.11 python3.11-venv python3-pip postgresql nginx git
```

---

### Шаг 3. Создать базу данных

```bash
sudo -u postgres psql -c "CREATE USER eye_user WITH PASSWORD 'eye_pass';"
sudo -u postgres psql -c "CREATE DATABASE eye_w OWNER eye_user;"
```

Пароль `eye_pass` можно заменить на свой — тогда его нужно будет указать в следующем шаге.

---

### Шаг 4. Скачать код проекта

**Если код на GitHub:**

```bash
cd /opt
git clone https://github.com/Notplay34/eye_w.git
cd eye_w
```

**Если код копируете с компьютера (Windows PowerShell):**

```powershell
scp -r c:\dev\mreo\eye_w root@ВАШ_IP:/opt/eye_w
```

Потом на сервере: `cd /opt/eye_w`.

---

### Шаг 5. Настроить backend

```bash
cd /opt/eye_w/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Создать файл с настройками:

```bash
nano .env
```

Вставить (подставьте свой пароль БД, если меняли):

```
DATABASE_URL=postgresql+asyncpg://eye_user:eye_pass@localhost:5432/eye_w
JWT_SECRET=придумайте_длинный_секретный_ключ_минимум_32_символа
```

Сохранить: `Ctrl+O`, `Enter`, `Ctrl+X`.

---

### Шаг 6. Создать сервис и nginx

Скопировать и выполнить:

```bash
cat > /etc/systemd/system/eye_w.service << 'EOF'
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
EOF

systemctl daemon-reload
systemctl enable eye_w
systemctl start eye_w
```

Настроить nginx:

```bash
cp /opt/eye_w/deploy/nginx-eye_w.conf /etc/nginx/sites-available/eye_w
ln -sf /etc/nginx/sites-available/eye_w /etc/nginx/sites-enabled/eye_w
nginx -t
systemctl reload nginx
```

---

### Шаг 7. Проверить

Откройте в браузере:

- `http://ВАШ_IP` — должна открыться страница входа.
- Войдите: **sergey151** / **1wq21wq2** (создаётся автоматически при первом запуске).

Если страница открылась и вход прошёл — всё работает.

**Если видите «Welcome to nginx!»** вместо формы входа — отключите стандартный сайт nginx:

```bash
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

**После первого входа** рекомендуется сменить пароль суперпользователя: Меню → Управление аккаунтами → выбрать «Сергей» → задать новый пароль.

---

## Если что-то пошло не так

**Сайт не открывается:**
- Проверьте: `systemctl status eye_w` — сервис должен быть `active (running)`.
- Проверьте: `curl http://127.0.0.1:8000/health` — должен вернуть `{"status":"ok"}`.

**Не входит в систему:**
- Убедитесь, что в `backend/.env` есть `JWT_SECRET`.
- Перезапустите: `systemctl restart eye_w`.

**Ошибка базы данных:**
- Проверьте, что PostgreSQL запущен: `systemctl status postgresql`.
- Проверьте пароль в `DATABASE_URL` в `backend/.env`.

**«Внутренняя ошибка сервера» при нажатии «Принять наличные»:**
- Касса в системе не нужна — платёж пишется в БД. Ошибка чаще всего из‑за схемы БД или прав.
- На сервере посмотрите лог: `journalctl -u eye_w --no-pager -n 50` — в конце будет текст ошибки (например, нет колонки `public_id`).
- После обновления кода выполните `systemctl restart eye_w` — при старте недостающие колонки в таблицах добавляются автоматически.

---

## Резервное копирование БД (рекомендуется)

Периодически сохраняйте копию базы на сервере или скачивайте на свой компьютер:

```bash
su - postgres -c "pg_dump eye_w" > /root/eye_w_backup_$(date +%Y%m%d).sql
```

Восстановление (если понадобится): `psql -U eye_user eye_w < файл_бэкапа.sql`.

---

## Обновление после изменений в коде

```bash
cd /opt/eye_w
git pull
systemctl restart eye_w
```

Или одной командой (если используете setup_server.sh):

```bash
cd /opt/eye_w && git pull && bash deploy/setup_server.sh
```

---

## Опционально: Django-подсистема (для частичных платежей и будущих фич)

В папке `django_backend/` есть дополнительный слой на Django. Он не обязателен для базовой работы. Подробности — в `django_backend/README.md`.
