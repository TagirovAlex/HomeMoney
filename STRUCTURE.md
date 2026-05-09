# Структура проекта HomeMoney

```
HomeMoney/
│
├── app.py                         # Flask entrypoint + все API-маршруты и страницы
├── config.py                      # Центральная конфигурация из .env
├── seed_demo.py                   # Наполнение демо-данными
│
├── install.sh                     # Интерактивный установщик для Debian 12
├── uninstall.sh                   # Скрипт полного удаления из системы
│
├── .env.example                   # Шаблон конфигурации
├── .gitignore
│
├── models/
│   └── database.py                # ORM-модели: User, Category, Transaction, Budget, IncomeSource
│
├── services/
│   ├── auth_service.py            # JWT (create/verify token), bcrypt (hash/verify password), require_auth
│   └── financial_service.py       # Бизнес-логика: транзакции, бюджеты, отчёты
│
├── data_access/
│   └── repositories/              # Data Access Layer (Repository Pattern)
│       ├── user_repository.py     # IUserRepository + SQLAlchemyUserRepository
│       ├── transaction_repository.py  # ITransactionRepository + SQLAlchemyTransactionRepository
│       ├── budget_repository.py   # IBudgetRepository + SQLAlchemyBudgetRepository
│       └── income_repository.py   # IIncomeSourceRepository + SQLAlchemyIncomeSourceRepository
│
├── utils/
│   ├── database_session.py        # Lazy SQLite engine + context manager get_db()
│   └── backup_service.py          # Полная копия SQLite + JSON-экспорт
│
├── telegram_bot.py                # Aiogram 3.x бот (SOCKS proxy, whitelist, wizard)
│
├── templates/                     # Jinja2 шаблоны (8 страниц)
│   ├── base.html                  # Базовый layout (навигация, тема, auth)
│   ├── login.html                 # Вход / Регистрация
│   ├── index.html                 # Дашборд (сводка за месяц)
│   ├── transactions.html          # Список транзакций + добавление
│   ├── incomes.html               # Источники дохода
│   ├── budgets.html               # Бюджеты по категориям
│   ├── reports.html               # Отчёты по месяцам
│   ├── admin.html                 # Админ-панель (пользователи, категории, бэкапы)
│   └── error.html                 # 403 / 404 / 500
│
├── static/
│   └── css/
│       └── style.css              # Единый CSS (светлая/тёмная тема, responsive)
│
└── tests/                         # Тесты (31 шт.)
    ├── test_auth_service.py       # Unit-тесты AuthService
    ├── test_financial_service.py  # Unit-тесты FinancialService
    └── test_api.py                # Интеграционные тесты API
```

## Слои архитектуры (Clean Architecture)

```
HTTP Request → Flask Route → require_auth (JWT) → Service Layer → Repository → SQLite
                                                                      ↑
Telegram Bot → aiogram Handler → Service Layer → Repository → SQLite
```

1. **Models** (`models/`) — описание сущностей БД
2. **Repositories** (`data_access/repositories/`) — абстрактные интерфейсы + реализации SQLAlchemy
3. **Services** (`services/`) — бизнес-логика (use cases)
4. **Presentation** (`app.py`, `telegram_bot.py`, `templates/`) — точки входа
