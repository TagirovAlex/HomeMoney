# Структура проекта HomeMoney

```
HomeMoney/
│
├── app.py                         # Flask entrypoint + все API-маршруты и страницы
├── config.py                      # Центральная конфигурация из .env (+ get_proxy_url)
├── seed_demo.py                   # Наполнение демо-данными
├── seed_default.py                # Базовые категории с эмодзи (10 шт.)
│
├── install.sh                     # Интерактивный установщик для Debian 12
├── uninstall.sh                   # Скрипт полного удаления из системы
│
├── .env.example                   # Шаблон конфигурации
├── .gitignore
├── requirements.txt
│
├── models/
│   └── database.py                # ORM-модели: User, Category (+ icon),
│                                  # Transaction, Budget, IncomeSource
│
├── services/
│   ├── auth_service.py            # JWT (create/verify token), bcrypt, require_auth
│   └── financial_service.py       # Бизнес-логика: транзакции, бюджеты, отчёты,
│                                  # регулярные доходы, пагинация, фильтры
│
├── data_access/
│   └── repositories/             # Data Access Layer (Repository Pattern)
│       ├── base_repository.py     # Базовый ABC + SQLAlchemyGenericRepository
│       ├── user_repository.py     # IUserRepository + SQLAlchemyUserRepository
│       ├── transaction_repository.py  # ITransactionRepository + реализация
│       ├── budget_repository.py   # IBudgetRepository + реализация (+ update/delete)
│       └── income_repository.py   # IIncomeSourceRepository + реализация (+ due)
│
├── utils/
│   ├── database_session.py        # Lazy SQLite engine + get_db() + _run_migrations
│   ├── backup_service.py          # Полная копия SQLite + JSON-экспорт
│   ├── bot_manager.py             # PID subprocess manager (start/stop/status)
│   ├── env_manager.py             # Чтение/запись .env из админ-панели
│   └── proxy_session.py           # 🔄 SOCKS5 proxy helper (aiogram + aiohttp)
│                                  #   create_aiogram_session(proxy_url)
│                                  #   create_aiogram_bot(token, proxy_url)
│                                  #   create_aiohttp_session(proxy_url)
│
├── handlers/
│   └── command_handlers.py        # Все команды бота + per-user sessions + auth
│
├── telegram_bot.py                # Aiogram 3.x бот (proxy, whitelist, webhook clean)
│
├── templates/                     # Jinja2 шаблоны (9 страниц)
│   ├── base.html                  # Базовый layout (навигация, тема, authHeaders)
│   ├── login.html                 # Вход / Регистрация
│   ├── index.html                 # Дашборд (сводка за текущий месяц)
│   ├── transactions.html          # Список + фильтр (месяц/год/категория) + пагинация
│   ├── incomes.html               # Источники дохода (+ edit/delete/process)
│   ├── budgets.html               # Бюджеты по категориям (+ edit/delete inline)
│   ├── reports.html               # Отчёты по категориям за месяц
│   ├── categories.html            # CRUD категорий с иконками
│   ├── admin.html                 # Админ-панель (users/categories/bot/backup/settings)
│   └── error.html                 # 403 / 404 / 500
│
├── static/
│   ├── css/
│   │   └── style.css              # Единый CSS (светлая/тёмная тема, responsive)
│   └── favicon.ico                # Иконка (синий круг + HM)
│
├── tests/                         # Тесты (44 шт.)
│   ├── test_auth_service.py       # Unit-тесты AuthService
│   ├── test_financial_service.py  # Unit-тесты FinancialService (+ process_regular)
│   └── test_api.py                # Интеграционные тесты API, страниц, RBAC, CRUD
│
├── DOCUMENTATION.md               # Полное руководство по развёртыванию
├── README.md                      
├── STRUCTURE.md                   
├── TODO.md                        
└── AGENTS.md                      # Инструкции для ИИ-агента
```

## Слои архитектуры (Clean Architecture)

```
HTTP Request → Flask Route → require_auth (JWT) → Service Layer → Repository → SQLite
                                                                      ↑
Telegram Bot → aiogram Handler → Service Layer → Repository → SQLite
                                   ↑
                            proxy_session.py (SOCKS5)
```

1. **Models** (`models/`) — описание сущностей БД
2. **Repositories** (`data_access/repositories/`) — абстрактные интерфейсы + SQLAlchemy реализации
3. **Services** (`services/`) — бизнес-логика (use cases)
4. **Presentation** (`app.py`, `telegram_bot.py`, `templates/`) — точки входа
5. **Utils** (`utils/`) — инфраструктурные утилиты (БД, бэкапы, прокси, env)

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
