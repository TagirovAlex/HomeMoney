# HomeMoney — Личный финансовый трекер

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue?logo=telegram)](https://docs.aiogram.dev/)
[![Tests](https://img.shields.io/badge/tests-44%20passed-green)]()

Веб-приложение для учёта личных финансов с веб-интерфейсом и Telegram-ботом. Реализована полноценная JWT-авторизация, ролевая модель (Admin/User), управление бюджетами, отчёты, регулярные доходы и резервное копирование.

---

## Возможности

- **Управление транзакциями** — доходы/расходы с привязкой к категориям, фильтрация по месяцу/году/категории, пагинация
- **Бюджетирование** — месячные лимиты по категориям с контролем превышения
- **Отчёты** — детализация расходов в разрезе категорий с бюджетом за выбранный период
- **Источники дохода** — регулярные и разовые поступления с автогенерацией транзакций
- **JWT-авторизация** — bcrypt + токены, роли Admin / User
- **Подтверждение регистрации** — администратор утверждает новых пользователей
- **Telegram-бот** — команды: `/start`, `/login`, `/addtx`, `/tx`, `/report`, `/budgets`, `/incomes`; SOCKS5 прокси; whitelist; автологин по telegram_id
- **Админ-панель** — управление пользователями, категориями, настройками бота, просмотр статуса бота, проверка прокси, бэкапы
- **Backup** — полная копия SQLite и JSON-экспорт
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
pip install -r requirements.txt

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
| `HM_BOT_PROXY_HOST` | Хост SOCKS5 прокси | `""` |
| `HM_BOT_PROXY_PORT` | Порт SOCKS5 прокси | `""` |
| `HM_BOT_PROXY_USERNAME` | Логин SOCKS5 прокси | `""` |
| `HM_BOT_PROXY_PASSWORD` | Пароль SOCKS5 прокси | `""` |
| `HM_BOT_ALLOWED_USERS` | Whitelist Telegram ID (через запятую) | `""` (все) |

---

## Telegram Bot

```bash
# Убедитесь, что HM_BOT_TOKEN задан в .env
python telegram_bot.py
```

### Команды

| Команда | Описание |
|---|---|
| `/start` | Главное меню с inline-кнопками |
| `/login email пароль` | Вход в аккаунт |
| `/logout` | Выход |
| `/addtx` | Добавить транзакцию (пошаговый ввод) |
| `/tx` | Последние 10 транзакций |
| `/report [месяц год]` | Отчёт за месяц |
| `/budgets` | Мои бюджеты |
| `/incomes` | Мои доходы |
| `/help` | Справка |

### SOCKS5 прокси

Если Telegram заблокирован в вашем регионе, задайте SOCKS5 прокси в `.env`:

```
HM_BOT_PROXY_HOST=127.0.0.1
HM_BOT_PROXY_PORT=1080
HM_BOT_PROXY_USERNAME=user     # опционально
HM_BOT_PROXY_PASSWORD=pass     # опционально
```

Настройки прокси можно менять через админ-панель без редактирования `.env` вручную.

### Автологин

Если в админ-панели привязан `telegram_id` к пользователю, бот автоматически выполнит вход без `/login`.

---

## API Endpoints

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/v1/health` | Публичный | Health check |
| `POST` | `/api/v1/register` | Публичный | Регистрация |
| `POST` | `/api/v1/login` | Публичный | Вход |
| `GET` | `/api/v1/me` | Авторизован | Текущий пользователь |
| `GET` | `/api/v1/transactions` | Авторизован | Сводка за месяц |
| `GET` | `/api/v1/user/<id>/transactions` | Авторизован | Список транзакций (фильтр, пагинация) |
| `POST` | `/api/v1/user/<id>/create_transaction` | Авторизован | Создать транзакцию |
| `GET` | `/api/v1/budgets` | Авторизован | Список бюджетов |
| `POST` | `/api/v1/budgets` | Авторизован | Создать бюджет |
| `PUT` | `/api/v1/budgets/<id>` | Авторизован | Редактировать бюджет |
| `DELETE` | `/api/v1/budgets/<id>` | Авторизован | Удалить бюджет |
| `GET` | `/api/v1/reports` | Авторизован | Отчёт за месяц |
| `GET` | `/api/v1/categories` | Авторизован | Список категорий |
| `POST` | `/api/v1/categories` | Авторизован | Создать категорию |
| `PUT` | `/api/v1/categories/<id>` | Авторизован | Редактировать категорию |
| `DELETE` | `/api/v1/categories/<id>` | Авторизован | Удалить категорию |
| `GET` | `/api/v1/incomes` | Авторизован | Список доходов |
| `POST` | `/api/v1/incomes` | Авторизован | Создать доход |
| `PUT` | `/api/v1/incomes/<id>` | Авторизован | Редактировать доход |
| `DELETE` | `/api/v1/incomes/<id>` | Авторизован | Удалить доход |
| `POST` | `/api/v1/incomes/process` | Авторизован | Создать транзакции по регулярным доходам |
| `GET` | `/api/v1/users` | Admin | Все пользователи |
| `GET` | `/api/v1/users/pending` | Admin | Ожидающие подтверждения |
| `POST` | `/api/v1/users/<id>/approve` | Admin | Подтвердить пользователя |
| `POST` | `/api/v1/users/<id>/reject` | Admin | Отклонить пользователя |
| `PUT` | `/api/v1/users/<id>/telegram` | Admin | Привязать Telegram ID |
| `GET` | `/api/v1/backup` | Admin | Создать бэкап |
| `GET` | `/api/v1/admin/settings` | Admin | Настройки `.env` |
| `PUT` | `/api/v1/admin/settings` | Admin | Сохранить настройки `.env` |
| `POST` | `/api/v1/admin/bot/start` | Admin | Запустить бота |
| `POST` | `/api/v1/admin/bot/stop` | Admin | Остановить бота |
| `GET` | `/api/v1/admin/bot/status` | Admin | Статус бота |
| `POST` | `/api/v1/admin/bot/check-proxy` | Admin | Проверить прокси |

---

## SOCKS5 Proxy Session Helper

Модуль `utils/proxy_session.py` можно скопировать в любой Python-проект для работы с Telegram API через SOCKS5 прокси.

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

Зависимости: `aiogram>=3.0`, `aiohttp-socks>=0.8`.

---

## Тестирование

```bash
pip install pytest
python -m pytest tests/ -v
```

**44 теста**: unit-тесты AuthService и FinancialService + интеграционные тесты всех API-эндпоинтов, страниц, CRUD, фильтров, пагинации, RBAC.

---

## Тестовые учётные записи

| Email | Пароль | Роль | Статус |
|---|---|---|---|
| `admin@demo.com` | `admin` | Admin | active |
| `ivan@demo.com` | `123` | User | active |
| `petr@demo.com` | `123` | User | pending |

Запустите `python seed_demo.py` для наполнения демо-данными.

---

## Структура проекта

```
HomeMoney/
├── app.py                          # Flask entrypoint + 25+ API роутов + 9 страниц
├── config.py                       # .env config + get_proxy_url()
├── services/
│   ├── auth_service.py             # JWT + bcrypt + require_auth
│   └── financial_service.py        # Бизнес-логика
├── data_access/repositories/
│   ├── user_repository.py
│   ├── transaction_repository.py
│   ├── budget_repository.py
│   └── income_repository.py
├── models/database.py              # SQLAlchemy models
├── utils/
│   ├── database_session.py         # Lazy SQLite engine + migrations
│   ├── backup_service.py           # Full + JSON backup
│   ├── bot_manager.py              # PID subprocess manager
│   ├── env_manager.py              # Read/write .env
│   └── proxy_session.py            # 🔄 SOCKS5 proxy helper (переиспользуемый)
├── handlers/
│   └── command_handlers.py         # All bot command handlers
├── telegram_bot.py                 # Aiogram 3.x bot entrypoint
├── templates/                      # 9 HTML pages
│   ├── base.html, login.html, index.html
│   ├── transactions.html, incomes.html
│   ├── budgets.html, reports.html
│   ├── categories.html, admin.html, error.html
├── static/css/style.css            # Dark/light theme, responsive
├── tests/                          # 44 tests
├── seed_demo.py                    # Demo data seeder
├── seed_default.py                 # Default categories seeder
├── install.sh                      # Debian installer
├── uninstall.sh                    # Debian uninstaller
├── requirements.txt
├── .env.example
├── AGENTS.md
├── DOCUMENTATION.md
├── README.md
├── STRUCTURE.md
└── TODO.md
```

---

## Удаление

```bash
sudo bash uninstall.sh
```

Скрипт остановит systemd-сервис, удалит nginx-конфиги, SSL-сертификаты (опционально), виртуальное окружение, БД и `.env`.
