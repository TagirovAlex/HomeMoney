#!/bin/bash
set -euo pipefail

# =========================================
# HomeMoney Setup Script for Debian 12
# Версия: 2.0.0
# Назначение: Интерактивная установка с поддержкой production (nginx + systemd)
# =========================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}   HomeMoney — Интерактивная установка${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# --- Проверка ОС ---
if [ ! -f /etc/debian_version ]; then
    warn "Скрипт оптимизирован для Debian 12. Продолжение на свой страх и риск."
fi

# --- Проверка Python ---
PYTHON=""
for c in python3.11 python3 python; do
    if command -v "$c" &>/dev/null; then
        PYTHON="$c"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    err "Python 3 не найден. Установите: apt install python3 python3-venv python3-pip"
    exit 1
fi
ok "Python: $($PYTHON --version)"

# --- Проверка / установка pip и venv ---
if ! "$PYTHON" -m ensurepip --version &>/dev/null; then
    info "Установка python3-venv и python3-pip..."
    apt update && apt install -y python3-venv python3-pip
fi

# --- Виртуальное окружение ---
if [ -d venv ]; then
    warn "Виртуальное окружение уже существует. Будет пересоздано."
    rm -rf venv
fi
info "Создание виртуального окружения..."
"$PYTHON" -m venv venv
source venv/bin/activate
ok "Виртуальное окружение создано"

# --- Установка зависимостей ---
info "Установка Python зависимостей..."
pip install --upgrade pip setuptools wheel
pip install flask sqlalchemy aiogram bcrypt pyjwt python-dotenv aiohttp-socks gunicorn
ok "Зависимости установлены"

# --- Файл .env ---
generate_secret() {
    tr -dc 'A-Za-z0-9!@#$%^&*()_+-=' < /dev/urandom 2>/dev/null | head -c 40 || python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

if [ ! -f .env ]; then
    info "Создание .env из шаблона..."
    cp .env.example .env

    SECRET=$(generate_secret)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/change-me-to-random-secret-32-bytes!!/$SECRET/" .env
    else
        sed -i "s/change-me-to-random-secret-32-bytes!!/$SECRET/" .env
    fi

    # В production DEBUG=false
    echo -e "\n# Production" >> .env
    echo "HM_DEBUG=false" >> .env
    ok ".env создан с случайным HM_SECRET_KEY"
else
    warn ".env уже существует, пропускаем"
fi

# --- Интерактивный запрос администратора ---
echo ""
echo -e "${YELLOW}--- Создание администратора ---${NC}"
read -r -p "Email администратора (по умолчанию: admin@homemoney.com): " ADMIN_EMAIL
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@homemoney.com}"

while true; do
    read -r -s -p "Пароль администратора (мин. 6 символов): " ADMIN_PASS
    echo ""
    if [ ${#ADMIN_PASS} -lt 6 ]; then
        warn "Пароль слишком короткий"
        continue
    fi
    read -r -s -p "Повторите пароль: " ADMIN_PASS2
    echo ""
    if [ "$ADMIN_PASS" != "$ADMIN_PASS2" ]; then
        warn "Пароли не совпадают"
        continue
    fi
    break
done

# --- Инициализация БД ---
info "Инициализация базы данных..."
source venv/bin/activate
python -c "
from utils.database_session import init_db, reset_engine
reset_engine()
init_db()
print('Таблицы созданы')
"
ok "База данных инициализирована"

# --- Создание администратора ---
info "Создание администратора..."
export HM_ADMIN_EMAIL="$ADMIN_EMAIL"
export HM_ADMIN_PASS="$ADMIN_PASS"
export PROJECT_DIR="$PROJECT_DIR"
python << 'PYEOF'
import os, sys
sys.path.insert(0, os.environ.get('PROJECT_DIR', os.getcwd()))
from data_access.repositories.user_repository import SQLAlchemyUserRepository
from services.auth_service import AuthService

email = os.environ['HM_ADMIN_EMAIL']
password = os.environ['HM_ADMIN_PASS']

hashed = AuthService.hash_password(password)
repo = SQLAlchemyUserRepository()
existing = repo.get_by_email(email)
if existing:
    print('⚠️ Администратор с таким email уже существует, пропускаем')
else:
    user = repo.create({
        'email': email,
        'hashed_password': hashed,
        'role': 'Admin',
        'status': 'active'
    })
    print(f'✅ Администратор создан: {user.email}')
PYEOF
if [ $? -eq 0 ]; then ok "Администратор создан"; else warn "Не удалось создать администратора"; fi

# --- Выбор режима ---
echo ""
echo -e "${YELLOW}--- Режим установки ---${NC}"
echo "1) Разработка (dev) — запуск через python app.py"
echo "2) Продакшен (prod) — nginx + systemd + gunicorn"
read -r -p "Выберите режим [1/2] (по умолчанию 1): " DEPLOY_MODE
DEPLOY_MODE="${DEPLOY_MODE:-1}"

if [ "$DEPLOY_MODE" = "2" ]; then
    echo ""
    echo -e "${YELLOW}--- Продакшен установка ---${NC}"

    # --- Установка nginx ---
    if ! command -v nginx &>/dev/null; then
        info "Установка nginx..."
        apt update && apt install -y nginx
        ok "nginx установлен"
    else
        ok "nginx уже установлен"
    fi

    # --- Домен ---
    read -r -p "Домен (например, homemoney.example.com): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        DOMAIN="localhost"
        warn "Домен не указан, используется localhost"
    fi

    # --- SSL через certbot ---
    USE_SSL=false
    if [ "$DOMAIN" != "localhost" ]; then
        read -r -p "Настроить SSL через Let's Encrypt? [y/N]: " SSL_ANSWER
        if [[ "$SSL_ANSWER" =~ ^[YyДд]$ ]]; then
            USE_SSL=true
            if ! command -v certbot &>/dev/null; then
                info "Установка certbot..."
                apt install -y certbot python3-certbot-nginx
                ok "certbot установлен"
            fi
        fi
    fi

    # --- Пользователь для сервиса ---
    SERVICE_USER="${SUDO_USER:-$USER}"
    info "Сервис будет запущен от пользователя: $SERVICE_USER"

    # --- systemd service ---
    info "Создание systemd сервиса..."
    cat > /etc/systemd/system/homemoney.service <<SERVICEEOF
[Unit]
Description=HomeMoney Financial API
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:create_app()
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

    systemctl daemon-reload
    systemctl enable homemoney
    systemctl restart homemoney
    ok "systemd сервис homemoney запущен"

    # --- nginx config ---
    info "Создание nginx конфигурации..."
    cat > /etc/nginx/sites-available/homemoney <<NGINXEOF
server {
    listen 80;
    server_name $DOMAIN;

    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINXEOF

    if [ -f /etc/nginx/sites-enabled/default ]; then
        rm /etc/nginx/sites-enabled/default
    fi
    ln -sf /etc/nginx/sites-available/homemoney /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    ok "nginx настроен"

    # --- SSL ---
    if [ "$USE_SSL" = true ]; then
        info "Получение SSL сертификата..."
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN" || \
        certbot --nginx -d "$DOMAIN"
        ok "SSL настроен"
    fi

    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}   Продакшен установка завершена!${NC}"
    echo -e "${GREEN}   Приложение: http://$DOMAIN${NC}"
    if [ "$USE_SSL" = true ]; then
        echo -e "${GREEN}   HTTPS:       https://$DOMAIN${NC}"
    fi
    echo -e "${GREEN}   systemctl status homemoney${NC}"
    echo -e "${GREEN}================================================${NC}"
else
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}   Dev-установка завершена!${NC}"
    echo -e "${GREEN}   Запуск: source venv/bin/activate && python app.py${NC}"
    echo -e "${GREEN}================================================${NC}"
fi

echo ""
echo -e "${GREEN}✨ Установка HomeMoney успешно завершена!${NC}"
echo -e "   Email: ${CYAN}$ADMIN_EMAIL${NC}"
echo -e "   Для удаления: ${CYAN}sudo bash uninstall.sh${NC}"
