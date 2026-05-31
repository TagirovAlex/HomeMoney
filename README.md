# HomeMoney — Личный финансовый трекер

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue?logo=telegram)](https://docs.aiogram.dev/)
[![Tests](https://img.shields.io/badge/tests-45%20passed-green)]()

Веб-приложение для учёта личных финансов с веб-интерфейсом и Telegram-ботом. JWT-авторизация через HttpOnly cookie, ролевая модель (Admin/User), управление бюджетами, сбережениями, отчёты, регулярные доходы и резервное копирование.

---

## Возможности

- **Управление транзакциями** — доходы/расходы по категориям, фильтрация по датам/категории, пагинация, сортировка, редактирование, удаление
- **Категории с типом** — тип расход/доход задаётся один раз в категории, автоматически синхронизируется с транзакциями
- **Бюджетирование** — месячные лимиты по категориям с контролем превышения, подсказка бюджета при создании транзакции
- **Отчёты** — детализация расходов по категориям, остаток на начало/конец периода, обороты, список транзакций, разбивка сбережений; дата-пикер с пресетами; фильтр по категории; переключатель списка транзакций (для производительности)
- **Сбережения/Инвестиции** — депозиты, акции, облигации, наличные, другое; CRUD, общая сумма на дашборде и в отчётах
- **Источники дохода** — регулярные и разовые поступления с автогенерацией транзакций (daily/weekly/monthly/yearly)
- **JWT-авторизация** — bcrypt + HttpOnly cookie (с запасным Authorization header), роли Admin / User, подтверждение регистрации, rate limiting
- **Telegram-бот** — полный набор команд: `/start`, `/login`, `/logout`, `/addtx`, `/tx`, `/edittx`, `/report`, `/budgets`, `/incomes`, `/addcat`, `/delcat`, `/process`, `/help`; SOCKS5 прокси; whitelist; автологин по telegram_id
- **Админ-панель** — управление пользователями, категориями, настройками бота, проверка прокси, бэкапы, лимит транзакций на дашборде
- **Безопасность** — 25 из 34 уязвимостей закрыто (bcrypt, JWT 1ч, HttpOnly, rate limiting, токен-блоклист, заголовки безопасности)
- **Backup** — полная копия SQLite и JSON-экспорт
- **Тёмная/светлая тема** — на всех страницах, Mobile-first

---

## Быстрый старт

### Production на Debian 12

```bash
git clone https://github.com/yourname/HomeMoney.git && cd HomeMoney
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
nano .env
python seed_demo.py
python app.py
```

---

## Конфигурация

Все настройки через `.env`:

| Переменная | Описание | По умолчанию |
|---|---|---|
| `HM_SECRET_KEY` | Секрет для JWT (мин. 32 символа) | `change-me-to-random-secret-32-bytes!!` |
| `HM_DATABASE_URL` | Путь к SQLite | `sqlite:///./home_money.db` |
| `HM_DEBUG` | Режим отладки Flask | `false` |
| `HM_BOT_TOKEN` | Токен Telegram-бота | `""` (бот отключён) |
| `HM_BOT_PROXY_HOST` | Хост SOCKS5 прокси | `""` |
| `HM_BOT_PROXY_PORT` | Порт SOCKS5 прокси | `""` |
| `HM_BOT_PROXY_USERNAME` | Логин SOCKS5 прокси | `""` |
| `HM_BOT_PROXY_PASSWORD` | Пароль SOCKS5 прокси | `""` |
| `HM_BOT_ALLOWED_USERS` | Whitelist Telegram ID (через запятую) | `""` (все) |
| `HM_DASHBOARD_TX_LIMIT` | Лимит последних транзакций на дашборде | `10` |

---

## Telegram Bot

```bash
python telegram_bot.py
```

### Команды

| Команда | Описание |
|---|---|
| `/start` | Главное меню с inline-кнопками |
| `/login email [пароль]` | Двухшаговый вход / без пароля — запрос |
| `/logout` | Выход |
| `/addtx` | Добавить транзакцию (пошагово: категория → сумма → описание → дата; тип из категории) |
| `/tx [месяц год]` | Список с пагинацией (5/стр) и inline-навигацией |
| `/edittx <id>` | Пошаговое редактирование (сумма → категория → описание → дата) |
| `/report [месяц год]` | Отчёт за месяц (доходы, расходы, остатки, детализация, бюджет) |
| `/budgets` | Мои бюджеты |
| `/incomes` | Мои доходы |
| `/addcat` | Создать категорию |
| `/delcat` | Список → подтверждение → удаление |
| `/process` | Выполнить регулярные платежи |
| `/help` | Справка |

### SOCKS5 прокси

Если Telegram заблокирован в вашем регионе, задайте SOCKS5 прокси в `.env`:

```
HM_BOT_PROXY_HOST=127.0.0.1
HM_BOT_PROXY_PORT=1080
HM_BOT_PROXY_USERNAME=user     # опционально
HM_BOT_PROXY_PASSWORD=pass     # опционально
```

Настройки прокси также доступны через админ-панель.

### Автологин

Если в админ-панели привязан `telegram_id` к пользователю, бот автоматически выполнит вход без `/login`.

---

## API Endpoints

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/v1/health` | Публичный | Health check |
| `POST` | `/api/v1/register` | Публичный | Регистрация (требует подтверждения админом) |
| `POST` | `/api/v1/login` | Публичный | Вход (JWT в HttpOnly cookie + JSON) |
| `POST` | `/api/v1/logout` | Авторизован | Выход (сброс cookie + блоклист токена) |
| `GET` | `/api/v1/me` | Авторизован | Текущий пользователь |
| `GET` | `/api/v1/transactions` | Авторизован | Сводка за месяц |
| `GET` | `/api/v1/user/<id>/transactions` | Авторизован | Список с фильтром (даты/категория) и пагинацией |
| `GET` | `/api/v1/user/<id>/transactions/<tx>` | Авторизован | Детали транзакции |
| `POST` | `/api/v1/user/<id>/create_transaction` | Авторизован | Создать транзакцию |
| `PUT` | `/api/v1/user/<id>/transactions/<tx>` | Авторизован | Редактировать транзакцию |
| `DELETE` | `/api/v1/user/<id>/transactions/<tx>` | Авторизован | Удалить транзакцию |
| `GET` | `/api/v1/budgets` | Авторизован | Список бюджетов |
| `POST` | `/api/v1/budgets` | Авторизован | Создать бюджет |
| `PUT` | `/api/v1/budgets/<id>` | Авторизован | Редактировать бюджет |
| `DELETE` | `/api/v1/budgets/<id>` | Авторизован | Удалить бюджет |
| `GET` | `/api/v1/reports` | Авторизован | Отчёт (month/year или start_date/end_date, category_id, include_transactions) |
| `GET` | `/api/v1/categories` | Авторизован | Список категорий (с типом) |
| `POST` | `/api/v1/categories` | Авторизован | Создать категорию |
| `PUT` | `/api/v1/categories/<id>` | Авторизован | Редактировать категорию |
| `DELETE` | `/api/v1/categories/<id>` | Авторизован | Удалить категорию |
| `GET` | `/api/v1/incomes` | Авторизован | Список доходов |
| `POST` | `/api/v1/incomes` | Авторизован | Создать доход |
| `PUT` | `/api/v1/incomes/<id>` | Авторизован | Редактировать доход |
| `DELETE` | `/api/v1/incomes/<id>` | Авторизован | Удалить доход |
| `POST` | `/api/v1/incomes/process` | Авторизован | Создать транзакции по регулярным доходам |
| `GET` | `/api/v1/savings` | Авторизован | Список сбережений |
| `POST` | `/api/v1/savings` | Авторизован | Создать сбережение |
| `PUT` | `/api/v1/savings/<id>` | Авторизован | Редактировать сбережение |
| `DELETE` | `/api/v1/savings/<id>` | Авторизован | Удалить сбережение |
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

bot = create_aiogram_bot("TOKEN", "socks5://user:pass@127.0.0.1:1080")
await bot.send_message(chat_id, "<b>Hello</b>")

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

**45 тестов**: unit-тесты AuthService и FinancialService + интеграционные тесты всех API-эндпоинтов, страниц, CRUD, фильтров, пагинации, RBAC.

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
├── app.py                          # Flask entrypoint + 40+ API роутов + 10 страниц
├── config.py                       # .env config + get_proxy_params()
├── services/
│   ├── auth_service.py             # JWT + bcrypt + require_auth + token blacklist
│   └── financial_service.py        # Бизнес-логика (транзакции, бюджеты, отчёты, регулярные доходы, сбережения)
├── data_access/repositories/
│   ├── user_repository.py          # Пользователи (CRUD, статусы, telegram_id)
│   ├── transaction_repository.py   # Транзакции (CRUD, фильтры, пагинация, даты)
│   ├── budget_repository.py        # Бюджеты (CRUD, активные за период)
│   ├── income_repository.py        # Источники дохода (CRUD, due-regular)
│   └── saving_repository.py        # Сбережения (CRUD)
├── models/database.py              # SQLAlchemy: User, Category (+icon/+type), Transaction, Budget, IncomeSource, Saving
├── utils/
│   ├── database_session.py         # Lazy SQLite engine + get_db() + _run_migrations
│   ├── backup_service.py           # Full + JSON backup
│   ├── bot_manager.py              # PID subprocess manager
│   ├── env_manager.py              # Read/write .env
│   ├── proxy_session.py            # SOCKS5 proxy helper (переиспользуемый)
│   └── rate_limiter.py             # In-memory rate limiter
├── handlers/
│   └── command_handlers.py         # Все команды бота (per-user sessions, auth, wizard, inline)
├── telegram_bot.py                 # Aiogram 3.x bot (proxy, whitelist, webhook clean)
├── templates/                      # 10 HTML pages (включая savings.html)
├── static/
│   ├── css/style.css               # Dark/light theme, responsive (mobile: hamburger menu,
│   │                               #   card tables, single-column admin grid, unified filters)
│   ├── logo.jpg                    # Логотип
│   └── favicon.ico
├── tests/                          # 45 tests
├── seed_demo.py                    # Demo data seeder
├── seed_default.py                 # Default categories (10 expense + 2 income)
├── install.sh / uninstall.sh       # Debian installer / uninstaller
├── requirements.txt / .env.example
└── DOCUMENTATION.md / README.md / STRUCTURE.md / TODO.md / AGENTS.md
```

---

## Удаление

```bash
sudo bash uninstall.sh
```

Скрипт остановит systemd-сервис, удалит nginx-конфиги, SSL-сертификаты (опционально), виртуальное окружение, БД и `.env`.
