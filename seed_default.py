"""Создание базовых категорий и демо-данных для нового пользователя."""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utils.database_session import init_db
init_db()

from models.database import Category
from utils.database_session import get_db

DEFAULT_CATEGORIES = [
    ("Продукты", "🛒"),
    ("Кафе и рестораны", "🍽️"),
    ("Аренда жилья", "🏠"),
    ("Коммунальные услуги", "💡"),
    ("Транспорт", "🚗"),
    ("Связь и интернет", "📱"),
    ("Развлечения", "🎬"),
    ("Здоровье", "💊"),
    ("Одежда", "👕"),
    ("Прочее", "📦"),
]

with get_db() as s:
    existing = s.query(Category).count()
    if existing > 0:
        print(f"В базе уже есть {existing} категорий. Пропускаем создание базовых.")
    else:
        for name, icon in DEFAULT_CATEGORIES:
            s.add(Category(name=name, icon=icon))
        s.commit()
        print(f"Создано {len(DEFAULT_CATEGORIES)} базовых категорий.")

print()
print("Базовые категории готовы. Теперь вы можете:")
print("  - Добавить начальный остаток через Транзакции")
print("  - Настроить регулярные доходы в Доходы")
print("  - Установить лимиты бюджетов в Бюджеты")
print("  - Посмотреть отчёты в Отчёты")