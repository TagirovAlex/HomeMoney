# Структура проекта HomeMoney

```
HomeMoney/
│
├── app.py                         # Flask entrypoint + все API-маршруты и страницы
├── config.py                      # Центральная конфигурация из .env (+ get_proxy_params)
├── seed_demo.py                   # Наполнение демо-данными
├── seed_default.py                # Базовые категории с эмодзи (10 шт.)
│
├── install.sh                     # Интерактивный установщик для Debian 12
├── uninstall.sh                   # Скрипт полного удаления из системы
│
├── .env.example                   # Шаблон конфигурации
├── .gitignore
├── requirements.txt               # Пинованные зависимости
│
├── models/
│   └── database.py                # ORM-модели: User, Category (+ icon/+ type),
│                                  # Transaction, Budget, IncomeSource, Saving
│
├── services/
│   ├── auth_service.py            # JWT (create/verify), bcrypt, require_auth,
│                                  # _extract_token (cookie + header), token blacklist
│   └── financial_service.py       # Бизнес-логика: транзакции, бюджеты, отчёты,
│                                  # регулярные доходы, сбережения, пагинация, фильтры
│
├── data_access/
│   └── repositories/             # Data Access Layer (Repository Pattern)
│       ├── user_repository.py     # IUserRepository + SQLAlchemyUserRepository
│       ├── transaction_repository.py  # ITransactionRepository + реализация (+ даты, пагинация)
│       ├── budget_repository.py   # IBudgetRepository + реализация (+ update/delete)
│       ├── income_repository.py   # IIncomeSourceRepository + реализация (+ due-regular)
│       └── saving_repository.py   # SavingRepository (CRUD для сбережений)
│
├── utils/
│   ├── database_session.py        # Lazy SQLite engine + get_db() + _run_migrations
│   ├── backup_service.py          # Полная копия SQLite + JSON-экспорт
│   ├── bot_manager.py             # PID subprocess manager (start/stop/status)
│   ├── env_manager.py             # Чтение/запись .env из админ-панели
│   ├── proxy_session.py           # 🔄 SOCKS5 proxy helper (aiogram + aiohttp)
│   │                              #   create_aiogram_session(proxy_url)
│   │                              #   create_aiogram_bot(token, proxy_url)
│   │                              #   create_aiohttp_session(proxy_url)
│   └── rate_limiter.py            # In-memory RateLimiter (login/register/bot)
│
├── handlers/
│   └── command_handlers.py        # Все команды бота + per-user sessions + auth +
│                                  # пошаговые wizard-ы + inline-пагинация
│
├── telegram_bot.py                # Aiogram 3.x бот (proxy, whitelist, webhook clean)
│
├── templates/                     # Jinja2 шаблоны (10 страниц)
│   ├── base.html                  # Базовый layout (навигация, тема, authHeaders, fmt)
│   ├── login.html                 # Вход / Регистрация
│   ├── index.html                 # Дашборд (сводка за месяц + сбережения)
│   ├── transactions.html          # Список + фильтр (даты + категория) + пагинация + сортировка
│   ├── incomes.html               # Источники дохода (+ edit/delete/process)
│   ├── savings.html               # Сбережения/Инвестиции (+ CRUD)
│   ├── budgets.html               # Бюджеты по категориям (+ edit/delete inline)
│   ├── reports.html               # Отчёты с дата-пикером, пресетами, фильтром по категории,
│                                  #   переключателем списка транзакций
│   ├── categories.html            # CRUD категорий с иконками
│   ├── admin.html                 # Админ-панель (users/bot/backup/settings/limits)
│   └── error.html                 # 403 / 404 / 500
│
├── static/
│   ├── css/
│   │   └── style.css              # Единый CSS (светлая/тёмная тема, responsive, админ-сетка)
│   ├── logo.jpg                   # Логотип
│   └── favicon.ico                # Иконка
│
├── tests/                         # Тесты (45 шт.)
│   ├── test_auth_service.py       # Unit-тесты AuthService
│   ├── test_financial_service.py  # Unit-тесты FinancialService (+ process_regular)
│   └── test_api.py                # Интеграционные тесты API, страниц, RBAC, CRUD, фильтров
│
├── DOCUMENTATION.md               # Полное руководство по развёртыванию
├── README.md
├── STRUCTURE.md
├── TODO.md
└── AGENTS.md                      # Инструкции для ИИ-агента
```

## Слои архитектуры (Clean Architecture)

```
HTTP Request → Flask Route → require_auth (JWT cookie) → Service Layer → Repository → SQLite
                                                                         ↑
Telegram Bot → aiogram Handler → Service Layer → Repository → SQLite
                                   ↑
                            proxy_session.py (SOCKS5)
```

1. **Models** (`models/`) — описание сущностей БД
2. **Repositories** (`data_access/repositories/`) — абстрактные интерфейсы + SQLAlchemy реализации
3. **Services** (`services/`) — бизнес-логика (use cases)
4. **Presentation** (`app.py`, `telegram_bot.py`, `templates/`) — точки входа
5. **Utils** (`utils/`) — инфраструктурные утилиты (БД, бэкапы, прокси, env, rate limiter)

## Поток данных для Telegram бота через SOCKS5

```
Telegram API  ←[SOCKS5]→  proxy_session.create_aiogram_session()
                                    ↓
                            telegram_bot.py (main)
                                    ↓
                            handlers/command_handlers.py
                                    ↓
                            FinancialService / AuthService
                                    ↓
                            SQLAlchemyRepository → SQLite
```
