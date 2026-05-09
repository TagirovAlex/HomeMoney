# HomeMoney: Руководство по развертыванию и эксплуатации

## Введение

Документ описывает архитектуру, требования к окружению и все способы запуска приложения для управления личными финансами.

---

## Требования к окружению

- **ОС:** Debian 12 (Bookworm) или новее
- **Python:** 3.10+
- **БД:** SQLite (встроенная, внешних СУБД не требуется)

---

## Установка

### Быстрая (рекомендуется)

```bash
sudo bash install.sh
```

Интерактивный скрипт выполнит:
1. Проверку и установку Python-зависимостей
2. Генерацию `.env` со случайным `HM_SECRET_KEY`
3. Создание администратора (email/пароль запрашиваются)
4. Выбор режима: разработка или продакшен (nginx + systemd)

### Ручная

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask sqlalchemy aiogram bcrypt pyjwt python-dotenv aiohttp-socks gunicorn

cp .env.example .env
# Отредактируйте секреты
nano .env

python seed_demo.py   # демо-данные + админ
python app.py         # запуск
```

---

## Режимы запуска

### Режим разработки

```bash
source venv/bin/activate
python app.py
# → http://localhost:5000
```

### Production (nginx + systemd)

**Автоматически** — выберите "2) Продакшен" в `install.sh`.

**Вручную:**

1. Установите gunicorn: `pip install gunicorn`
2. Создайте systemd-сервис `/etc/systemd/system/homemoney.service`:
```ini
[Unit]
Description=HomeMoney Financial API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/HomeMoney
Environment=PATH=/opt/HomeMoney/venv/bin
ExecStart=/opt/HomeMoney/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:create_app()
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
3. `systemctl daemon-reload && systemctl enable --now homemoney`
4. Настройте nginx (см. ниже).

---

## Настройка nginx

### Базовая конфигурация (HTTP)

```nginx
server {
    listen 80;
    server_name homemoney.example.com;

    location /static/ {
        alias /opt/HomeMoney/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Свой SSL-сертификат

Если у вас есть собственный SSL-сертификат (не Let's Encrypt):

```nginx
server {
    listen 443 ssl http2;
    server_name homemoney.example.com;

    ssl_certificate     /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;

    # Опционально: ssl_client_certificate для цепочки
    # ssl_trusted_certificate /path/to/ca-cert.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /static/ {
        alias /opt/HomeMoney/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name homemoney.example.com;
    return 301 https://$host$request_uri;
}
```

Примените:
```bash
nginx -t && systemctl reload nginx
```

### Let's Encrypt (автоматически)

При выборе production-режима в `install.sh` скрипт сам установит certbot и получит сертификат. Для ручного запуска:

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d homemoney.example.com
```

---

## Telegram Bot

```bash
export HM_BOT_TOKEN="your:bot:token"
python telegram_bot.py
```

Бот поддерживает:
- **SOCKS5/SOCKS4/HTTP прокси** — задаётся в `HM_BOT_PROXY_URL`
- **Whitelist** — `HM_BOT_ALLOWED_USERS` (Telegram ID через запятую, пусто = все)
- **Пошаговый ввод** — выбор категории → сумма → описание

---

## Бэкапы

Через админ-панель (`/admin`) или API:

```bash
# Полная копия SQLite
curl -H "Authorization: Bearer <token>" /api/v1/backup?type=full

# JSON-экспорт всех таблиц
curl -H "Authorization: Bearer <token>" /api/v1/backup?type=json
```

---

## Тестирование

```bash
python -m pytest tests/ -v
```

Покрытие: 31 тест (unit + integration auth, financial service, API endpoints).

---

## Удаление

```bash
sudo bash uninstall.sh
```

Скрипт остановит сервисы, удалит nginx-конфиги, SSL-сертификаты, venv, БД и `.env` (с подтверждением каждого шага).
