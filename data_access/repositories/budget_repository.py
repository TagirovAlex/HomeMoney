from abc import ABC, abstractmethod
from typing import List, Optional
from models.database import Budget 
from utils.database_session import get_db # Используем контекстный менеджер для сессии

class IBudgetRepository(ABC):
    """Интерфейс репозитория для работы с бюджетами."""

    @abstractmethod
    def get_active_budgets_for_user(self, user_id: int, month: int, year: int) -> List[Budget]:
        pass

class SQLAlchemyBudgetRepository:
    """Рабочий репозиторий бюджетов с использованием SQLAlchemy."""

    def __init__(self):
        self._db = get_db

    # --- Методы реализации IBudgetRepository ---
    
    def get_active_budgets_for_user(self, user_id: int, month: int, year: int) -> List[Budget]:
        from datetime import date, timedelta 
        try:
            start = date(year, month, 1)
            end_month = start + timedelta(days=32)
            end = (end_month.replace(day=1) - timedelta(days=1)) # Последний день месяца
        except ValueError:
             return []

        with self._db() as session:
            return session.query(Budget).filter(
                Budget.user_id == user_id, 
                Budget.period_start_date <= end
            ).all()

    def create_budget(self, budget_data: dict) -> Budget:
        with self._db() as session:
            new_budget = Budget(**budget_data)
            session.add(new_budget)
            session.commit()
            session.refresh(new_budget)
            return new_budget