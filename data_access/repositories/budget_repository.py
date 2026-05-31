from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy import or_, and_
from models.database import Budget 
from utils.database_session import get_db

class IBudgetRepository(ABC):
    @abstractmethod
    def get_active_budgets_for_user(self, user_id: int, month: int, year: int) -> List[Budget]:
        pass

    @abstractmethod
    def create_budget(self, budget_data: dict) -> Budget:
        pass

    @abstractmethod
    def get_all_for_user(self, user_id: int) -> List[Budget]:
        pass

    @abstractmethod
    def update_budget(self, budget_id: int, user_id: int, data: dict) -> Optional[Budget]:
        pass

    @abstractmethod
    def delete_budget(self, budget_id: int, user_id: int) -> bool:
        pass

    @abstractmethod
    def get_templates(self, user_id: int) -> List[Budget]:
        pass

    @abstractmethod
    def get_overrides_for_month(self, user_id: int, month: int, year: int) -> List[Budget]:
        pass

    @abstractmethod
    def get_template_for_category(self, user_id: int, category_id: int) -> Optional[Budget]:
        pass

    @abstractmethod
    def get_override(self, user_id: int, category_id: int, month: int, year: int) -> Optional[Budget]:
        pass

class SQLAlchemyBudgetRepository(IBudgetRepository):

    def __init__(self):
        self._db = get_db

    def get_active_budgets_for_user(self, user_id: int, month: int, year: int) -> List[Budget]:
        """Возвращает бюджеты, действующие в указанном месяце:
        шаблоны + переопределения для этого месяца. Если есть и шаблон,
        и переопределение на одну категорию — побеждает переопределение."""
        with self._db() as session:
            budgets = session.query(Budget).filter(
                Budget.user_id == user_id,
                or_(
                    and_(Budget.month.is_(None), Budget.year.is_(None)),
                    and_(Budget.month == month, Budget.year == year)
                )
            ).all()
            resolved = {}
            for b in budgets:
                if b.category_id not in resolved or (b.month is not None and b.year is not None):
                    resolved[b.category_id] = b
            return list(resolved.values())

    def create_budget(self, budget_data: dict) -> Budget:
        with self._db() as session:
            new_budget = Budget(**budget_data)
            session.add(new_budget)
            session.commit()
            session.refresh(new_budget)
            return new_budget

    def get_all_for_user(self, user_id: int) -> List[Budget]:
        with self._db() as session:
            return session.query(Budget).filter(Budget.user_id == user_id).all()

    def update_budget(self, budget_id: int, user_id: int, data: dict) -> Optional[Budget]:
        with self._db() as session:
            b = session.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
            if not b:
                return None
            for k, v in data.items():
                setattr(b, k, v)
            session.commit()
            session.refresh(b)
            return b

    def delete_budget(self, budget_id: int, user_id: int) -> bool:
        with self._db() as session:
            b = session.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
            if not b:
                return False
            session.delete(b)
            session.commit()
            return True

    def get_templates(self, user_id: int) -> List[Budget]:
        with self._db() as session:
            return session.query(Budget).filter(
                Budget.user_id == user_id,
                Budget.month.is_(None),
                Budget.year.is_(None)
            ).all()

    def get_overrides_for_month(self, user_id: int, month: int, year: int) -> List[Budget]:
        with self._db() as session:
            return session.query(Budget).filter(
                Budget.user_id == user_id,
                Budget.month == month,
                Budget.year == year
            ).all()

    def get_template_for_category(self, user_id: int, category_id: int) -> Optional[Budget]:
        with self._db() as session:
            return session.query(Budget).filter(
                Budget.user_id == user_id,
                Budget.category_id == category_id,
                Budget.month.is_(None),
                Budget.year.is_(None)
            ).first()

    def get_override(self, user_id: int, category_id: int, month: int, year: int) -> Optional[Budget]:
        with self._db() as session:
            return session.query(Budget).filter(
                Budget.user_id == user_id,
                Budget.category_id == category_id,
                Budget.month == month,
                Budget.year == year
            ).first()