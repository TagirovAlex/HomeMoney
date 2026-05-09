# HomeMoney — Личный финансовый трекер

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue?logo=telegram)](https://docs.aiogram.dev/)
[![Tests](https://img.shields.io/badge/tests-31%20passed-green)]()

Веб-приложение для учёта личных финансов с веб-интерфейсом и Telegram-ботом. Реализована полноценная JWT-авторизация, ролевая модель (Admin/User), управление бюджетами, отчёты и резервное копирование.

---

## Возможности

- **Управление транзакциями** — доходы/расходы с привязкой к категориям
- **Бюджетирование** — месячные лимиты по категориям с контролем превышения
- **Отчёты** — детализация расходов в разрезе категорий за выбранный период
- **Источники дохода** — учёт регулярных и разовых поступлений
- **JWT-авторизация** — bcrypt + токены, роли Admin / User
- **Подтверждение регистрации** — администратор утверждает новых пользователей
- **Telegram-бот** — ввод транзакций через диалог (aiogram 3.x, SOCKS5/SOCKS4/HTTP proxy, whitelist)
- **Backup** — полная копия SQLite и JSON-экспорт через админ-панель
- **Тёмная/светлая тема** — на всех страницах
- **Mobile-first** — адаптивный дизайн

---

## Быстрый старт

### Production на Debian 12

```bash
# Клонирование
git clone https://github.com/yourname/HomeMoney.git && cd HomeMoney

# Интерактивная установка
sudo bash install.sh
```

Скрипт:
1. Установит Python-зависимости в виртуальное окружение
2. Сгенерирует `.env` со случайным `HM_SECRET_KEY`
3. Запросит email/пароль администратора
4. Предложит выбор: **dev** (`python app.py`) или **prod** (nginx + systemd + gunicorn)
5. В prod-режиме настроит reverse-proxy и опционально Let's Encrypt SSL

### Ручная установка

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask sqlalchemy aiogram bcrypt pyjwt python-dotenv aiohttp-socks gunicorn

cp .env.example .env
# Отредактируйте HM_SECRET_KEY, HM_BOT_TOKEN и пр.
nano .env

# Инициализация БД и создание администратора
python seed_demo.py

# Запуск
python app.py
```

---

## Конфигурация

Все настройки через `.env`:

| Переменная | Описание | По умолчанию |
|---|---|---|
| `HM_SECRET_KEY` | Секрет для JWT (мин. 32 символа) | `change-me-to-random-secret-32-bytes!!` |
| `HM_DATABASE_URL` | Путь к SQLite | `sqlite:///./home_money.db` |
| `HM_DEBUG` | Режим отладки Flask | `true` |
| `HM_BOT_TOKEN` | Токен Telegram-бота | `""` (бот отключён) |
| `HM_BOT_PROXY_URL` | SOCKS/HTTP прокси для бота | `""` |
| `HM_BOT_ALLOWED_USERS` | Whitelist Telegram ID (через запятую) | `""` (все) |

---

## Production: nginx + systemd

### Автоматическая установка

При запуске `install.sh` выберите режим **2) Продакшен**. Скрипт:
- Установит `nginx`
- Настроит `gunicorn` с systemd-сервисом (`homemoney.service`)
- Создаст nginx reverse-proxy (`127.0.0.1:8000 → 80`)
- По запросу настроит SSL через Let's Encrypt

### Ручная настройка

**systemd-сервис** (`/etc/systemd/system/homemoney.service`):
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

```bash
systemctl daemon-reload && systemctl enable --now homemoney
```

### Свой SSL-сертификат

Если у вас есть собственный SSL-сертификат, отредактируйте `/etc/nginx/sites-available/homemoney`:

```nginx
server {
    listen 443 ssl http2;
    server_name homemoney.example.com;

    ssl_certificate     /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;

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

server {
    listen 80;
    server_name homemoney.example.com;
    return 301 https://$host$request_uri;
}
```

```bash
nginx -t && systemctl reload nginx
```

---

## Telegram Bot

```bash
# Убедитесь, что HM_BOT_TOKEN задан в .env
python telegram_bot.py
```

Бот поддерживает:
- SOCKS5/SOCKS4/HTTP прокси (`HM_BOT_PROXY_URL`)
- Whitelist пользователей (`HM_BOT_ALLOWED_USERS`)
- Пошаговый ввод транзакций (выбор категории → сумма → описание)

---

## Тестирование

```bash
pip install pytest
python -m pytest tests/ -v
```

Сейчас **31 тест**: unit-тесты AuthService и FinancialService + интеграционные тесты всех API-эндпоинтов.

---

## API Endpoints

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/v1/health` | Публичный | Health check |
| `POST` | `/api/v1/register` | Публичный | Регистрация |
| `POST` | `/api/v1/login` | Публичный | Вход |
| `GET` | `/api/v1/me` | Авторизован | Текущий пользователь |
| `GET` | `/api/v1/transactions` | Авторизован | Сводка за месяц |
| `GET` | `/api/v1/user/<id>/transactions` | Авторизован | Список транзакций |
| `POST` | `/api/v1/user/<id>/create_transaction` | Авторизован | Создать транзакцию |
| `GET` | `/api/v1/budgets` | Авторизован | Список бюджетов |
| `POST` | `/api/v1/budgets` | Авторизован | Создать бюджет |
| `GET` | `/api/v1/reports` | Авторизован | Отчёт за месяц |
| `GET` | `/api/v1/categories` | Авторизован | Список категорий |
| `POST` | `/api/v1/categories` | Авторизован | Создать категорию |
| `GET` | `/api/v1/incomes` | Авторизован | Список доходов |
| `POST` | `/api/v1/incomes` | Авторизован | Создать доход |
| `DELETE` | `/api/v1/incomes/<id>` | Авторизован | Удалить доход |
| `GET` | `/api/v1/users` | Admin | Все пользователи |
| `GET` | `/api/v1/users/pending` | Admin | Ожидающие подтверждения |
| `POST` | `/api/v1/users/<id>/approve` | Admin | Подтвердить пользователя |
| `POST` | `/api/v1/users/<id>/reject` | Admin | Отклонить пользователя |
| `GET` | `/api/v1/backup` | Admin | Создать бэкап |

---

## Структура проекта

```
HomeMoney/
├── app.py                          # Flask entrypoint + routes
├── config.py                       # .env config
├── services/
│   ├── auth_service.py             # JWT + bcrypt
│   └── financial_service.py        # Business logic
├── data_access/repositories/
│   ├── user_repository.py
│   ├── transaction_repository.py
│   ├── budget_repository.py
│   └── income_repository.py
├── models/database.py              # SQLAlchemy models
├── utils/
│   ├── database_session.py         # Lazy SQLite engine
│   └── backup_service.py           # Full + JSON backup
├── telegram_bot.py                 # Aiogram 3.x bot
├── templates/                      # 8 HTML pages
├── static/css/style.css            # Dark/light theme
├── tests/                          # 31 tests
├── seed_demo.py                    # Demo data seeder
├── install.sh                      # Debian installer
└── uninstall.sh                    # Debian uninstaller
```

---

## Тестовые учётные записи

| Email | Пароль | Роль | Статус |
|---|---|---|---|
| `admin@demo.com` | `admin` | Admin | active |
| `ivan@demo.com` | `123` | User | active |
| `petr@demo.com` | `123` | User | pending |

Запустите `python seed_demo.py` для наполнения демо-данными.

---

## Удаление

```bash
sudo bash uninstall.sh
```

Скрипт остановит systemd-сервис, удалит nginx-конфиги, SSL-сертификаты (опционально), виртуальное окружение, БД и `.env`.
