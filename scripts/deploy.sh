#!/bin/bash
# Развёртывание eye_w на Debian/Ubuntu (использует python3 из репозитория)
set -e

EYE_DIR="${EYE_DIR:-/opt/eye_w}"
DB_USER="${DB_USER:-eye_user}"
DB_PASS="${DB_PASS:-eye_pass}"
DB_NAME="${DB_NAME:-eye_w}"

echo "=== 1. Пакеты ==="
apt update
apt install -y python3 python3-venv python3-pip postgresql nginx git

echo "=== 2. PostgreSQL ==="
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
systemctl start postgresql 2>/dev/null || true

echo "=== 3. Код в $EYE_DIR ==="
if [ ! -d "$EYE_DIR" ]; then
  echo "Папка $EYE_DIR не найдена. Клонирую с GitHub."
  mkdir -p /opt
  git clone https://github.com/Notplay34/eye_w.git "$EYE_DIR"
else
  echo "Папка есть, обновляю (git pull)."
  (cd "$EYE_DIR" && git pull) || true
fi

echo "=== 4. Backend ==="
cd "$EYE_DIR/backend"
rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
if [ ! -f .env ]; then
  echo "DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME" > .env
  echo "Создан backend/.env"
fi

echo "=== 5. Systemd ==="
cat > /etc/systemd/system/eye_w.service << EOF
[Unit]
Description=Eye-W Backend
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=$EYE_DIR/backend
ExecStart=$EYE_DIR/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable eye_w
systemctl restart eye_w
echo "Backend: systemctl status eye_w"

echo "=== 6. Nginx ==="
SERVER_NAME="${SERVER_NAME:-_}"
cat > /etc/nginx/sites-available/eye_w << EOF
server {
    listen 80;
    server_name $SERVER_NAME;
    root $EYE_DIR/frontend;
    index index.html;
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    location /docs { proxy_pass http://127.0.0.1:8000; proxy_set_header Host \$host; }
    location /openapi.json { proxy_pass http://127.0.0.1:8000; proxy_set_header Host \$host; }
    location /health { proxy_pass http://127.0.0.1:8000; proxy_set_header Host \$host; }
    location /orders { proxy_pass http://127.0.0.1:8000; proxy_set_header Host \$host; proxy_set_header X-Real-IP \$remote_addr; }
    location /employees { proxy_pass http://127.0.0.1:8000; proxy_set_header Host \$host; }
    location /analytics { proxy_pass http://127.0.0.1:8000; proxy_set_header Host \$host; }
    location /auth { proxy_pass http://127.0.0.1:8000; proxy_set_header Host \$host; }
}
EOF
ln -sf /etc/nginx/sites-available/eye_w /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "=== Готово ==="
echo "Проверка backend: curl -s http://127.0.0.1:8000/health"
curl -s http://127.0.0.1:8000/health || true
echo ""
echo "Сайт: http://$(hostname -I | awk '{print $1}') или http://194.87.103.157"
