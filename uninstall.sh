#!/bin/bash
set -euo pipefail

# =========================================
# HomeMoney Uninstall Script
# Версия: 1.0.0
# Назначение: Полное удаление HomeMoney из системы
# =========================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${RED}================================================${NC}"
echo -e "${RED}   HomeMoney — Удаление из системы${NC}"
echo -e "${RED}================================================${NC}"
echo ""
warn "Это удалит HomeMoney и все связанные компоненты!"
read -r -p "Вы уверены? Введите 'yes' для подтверждения: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    info "Отмена"
    exit 0
fi

# --- 1. Остановка systemd сервиса ---
if systemctl is-active --quiet homemoney 2>/dev/null; then
    info "Остановка systemd сервиса..."
    systemctl stop homemoney
    ok "Сервис остановлен"
fi

if systemctl is-enabled --quiet homemoney 2>/dev/null; then
    systemctl disable homemoney
    ok "Сервис отключён"
fi

if [ -f /etc/systemd/system/homemoney.service ]; then
    rm -f /etc/systemd/system/homemoney.service
    systemctl daemon-reload
    ok "systemd файл удалён"
fi

# --- 2. Удаление nginx конфигурации ---
if [ -f /etc/nginx/sites-enabled/homemoney ]; then
    rm -f /etc/nginx/sites-enabled/homemoney
    ok "nginx site-enabled ссылка удалена"
fi

if [ -f /etc/nginx/sites-available/homemoney ]; then
    rm -f /etc/nginx/sites-available/homemoney
    ok "nginx site-available конфиг удалён"
fi

# Перезагрузка nginx если он установлен
if command -v nginx &>/dev/null; then
    nginx -t 2>/dev/null && systemctl reload nginx && ok "nginx перезагружен" || warn "nginx не перезагружен (проверьте конфигурацию)"
fi

# --- 3. Удаление SSL сертификата (опционально) ---
if command -v certbot &>/dev/null; then
    read -r -p "Удалить SSL сертификаты Let's Encrypt? [y/N]: " SSL_ANSWER
    if [[ "$SSL_ANSWER" =~ ^[YyДд]$ ]]; then
        certbot delete --cert-name "$(certbot certificates 2>/dev/null | grep 'Certificate Name' | head -1 | awk '{print $3}')" 2>/dev/null || true
        ok "SSL сертификаты удалены"
    fi
fi

# --- 4. Удаление виртуального окружения ---
if [ -d "$PROJECT_DIR/venv" ]; then
    rm -rf "$PROJECT_DIR/venv"
    ok "Виртуальное окружение удалено"
fi

# --- 5. Удаление базы данных (опционально) ---
DB_FILE="$PROJECT_DIR/home_money.db"
if [ -f "$DB_FILE" ]; then
    read -r -p "Удалить базу данных ($DB_FILE)? [y/N]: " DB_ANSWER
    if [[ "$DB_ANSWER" =~ ^[YyДд]$ ]]; then
        rm -f "$DB_FILE"
        ok "База данных удалена"
    fi
fi

# --- 6. Удаление .env (опционально) ---
if [ -f "$PROJECT_DIR/.env" ]; then
    read -r -p "Удалить .env (содержит секреты и токены)? [y/N]: " ENV_ANSWER
    if [[ "$ENV_ANSWER" =~ ^[YyДд]$ ]]; then
        rm -f "$PROJECT_DIR/.env"
        ok ".env удалён"
    fi
fi

# --- 7. Очистка Python cache ---
find "$PROJECT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR" -type f -name '*.pyc' -delete 2>/dev/null || true
find "$PROJECT_DIR" -type f -name '*.pyo' -delete 2>/dev/null || true
ok "Кэш Python очищен"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   HomeMoney полностью удалён из системы${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Чтобы удалить сам проект, выполните:"
echo "  rm -rf $PROJECT_DIR"
echo ""
echo "Чтобы удалить зависимости (nginx, certbot), выполните:"
echo "  apt remove --purge nginx certbot python3-certbot-nginx"
echo "  apt autoremove"
