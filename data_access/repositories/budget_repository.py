from abc import ABC, abstractmethod
from typing import List, Optional
# Импорт реальной модели и утилиты сессии
from models.database import Budget 
from utils.database_session import get_db # Используем контекстный менеджер для сессии

class SQLAlchemyBudgetRepository(ABC):
    """Конкретная реализация репозитория бюджетов с использованием SQLAlchemy."""

    def __init__(self, db=None):
        self._db = get_db() 

    # --- Реализация интерфейса IBudgetRepository ---
    
    def get_active_budgets_for_user(self, user_id: int, month: int, year: int) -> List[Budget]:
        """Получить все активные бюджеты пользователя на указанный период."""
        from datetime import date, timedelta # Импорт здесь для чистоты
        # Определяем диапазон: начало месяца до последнего дня этого месяца.
        try:
            start = date(year, month, 1)
            end_month = start + timedelta(days=32)
            end = (end_month.replace(day=1) - timedelta(days=1)) # Последний день месяца
        except ValueError:
             return [] # Обработка некорректного месяца/года

        with self._db() as session:
            # Фильтрация по пользователю и активному периоду, покрывающему нужный месяц.
            # Здесь должна быть более сложная логика пересечения дат, но для MVP используем фильтр по диапазону.
            return session.query(Budget).filter(
                Budget.user_id == user_id, 
                Budget.period_start_date <= end # Простая проверка: началось до конца месяца
            ).all()

    def create_budget(self, budget_data: dict) -> Budget:
        """Создать новый бюджет."""
        with self._db() as session:
            new_budget = Budget(**budget_data)
            session.add(new_budget)
            session.commit()
            session.refresh(new_budget)
            return new_budget