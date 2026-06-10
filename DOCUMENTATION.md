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
5. В prod-режиме: настройка reverse-proxy, опционально Let's Encrypt SSL

### Ручная

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Отредактируйте секреты
# ⚠️ ОБЯЗАТЕЛЬНО замените HM_SECRET_KEY на случайную строку 32+ символов!
# Значение из .env.example (change-me-to-random-secret-32-bytes!!) легко угадать.
# В production приложение не запустится без установленного HM_SECRET_KEY.
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

### Запуск

```bash
# Убедитесь, что HM_BOT_TOKEN и (опционально) HM_BOT_PROXY_HOST заданы в .env
python telegram_bot.py
```

### Возможности

- **SOCKS5 прокси** — настройка через `.env`: `HM_BOT_PROXY_HOST`, `HM_BOT_PROXY_PORT`, `HM_BOT_PROXY_USERNAME`, `HM_BOT_PROXY_PASSWORD`
- **Whitelist** — `HM_BOT_ALLOWED_USERS` (Telegram ID через запятую, пусто = все)
- **Автологин** — если `telegram_id` пользователя сохранён в БД, бот не требует `/login`
- **Пошаговый ввод транзакций** — inline-кнопка → выбор категории → сумма → описание → дата
- **Пагинация** — `/tx` показывает 5 транзакций на страницу с inline-навигацией
- **Редактирование** — `/edittx <id>` с пошаговым изменением полей

### Управление из админ-панели

- `/admin` → карточка **Telegram Bot**: запуск/остановка, статус онлайн (`getMe`), проверка прокси
- Настройки бота и прокси сохраняются в `.env` через админ-панель

---

## SOCKS5 Proxy Session Helper

Модуль `utils/proxy_session.py` предоставляет переиспользуемые функции для создания HTTP-сессий с поддержкой SOCKS5 прокси. Может использоваться в других проектах независимо от HomeMoney.

### Функции

| Функция | Назначение |
|---|---|
| `create_aiogram_session(proxy_url)` | Создаёт `AiohttpSession` для aiogram |
| `create_aiogram_bot(token, proxy_url, parse_mode)` | Создаёт `Bot` с прокси и HTML-форматированием |
| `create_aiohttp_session(proxy_url)` | Создаёт `aiohttp.ClientSession` с прокси |

### Пример использования в другом проекте

```python
from proxy_session import create_aiogram_bot, create_aiohttp_session

# Telegram-бот с SOCKS5
bot = create_aiogram_bot("TOKEN", "socks5://user:pass@127.0.0.1:1080")
await bot.send_message(chat_id, "<b>Hello</b>")

# HTTP-запрос через SOCKS5
async with create_aiohttp_session("socks5://127.0.0.1:1080") as sess:
    async with sess.get("https://api.telegram.org") as resp:
        print(resp.status)
```

### Зависимости для копирования в другой проект

```
aiogram>=3.0
aiohttp-socks>=0.8
```

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

Покрытие: 45 тестов (unit + integration: auth, financial service, CRUD, фильтры, пагинация, RBAC, отчёты).

---

## Удаление

```bash
sudo bash uninstall.sh
```

Скрипт остановит сервисы, удалит nginx-конфиги, SSL-сертификаты, venv, БД и `.env` (с подтверждением каждого шага).
