from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, date
from models.database import IncomeSource
from utils.database_session import get_db

class IIncomeSourceRepository(ABC):
    @abstractmethod
    def get_by_user(self, user_id: int) -> List[IncomeSource]:
        pass

    @abstractmethod
    def get_by_id(self, income_id: int, user_id: int) -> Optional[IncomeSource]:
        pass

    @abstractmethod
    def create(self, data: dict) -> IncomeSource:
        pass

    @abstractmethod
    def update(self, income_id: int, user_id: int, data: dict) -> Optional[IncomeSource]:
        pass

    @abstractmethod
    def delete(self, income_id: int, user_id: int) -> bool:
        pass

    @abstractmethod
    def get_due_regular(self, user_id: int) -> List[IncomeSource]:
        pass

class SQLAlchemyIncomeSourceRepository:
    def __init__(self):
        self._db = get_db

    def get_by_user(self, user_id: int) -> List[IncomeSource]:
        with self._db() as session:
            return session.query(IncomeSource).filter(IncomeSource.user_id == user_id).all()

    def get_by_id(self, income_id: int, user_id: int) -> Optional[IncomeSource]:
        with self._db() as session:
            return session.query(IncomeSource).filter(
                IncomeSource.id == income_id, IncomeSource.user_id == user_id
            ).first()

    def create(self, data: dict) -> IncomeSource:
        with self._db() as session:
            src = IncomeSource(**data)
            session.add(src)
            session.commit()
            session.refresh(src)
            return src

    def update(self, income_id: int, user_id: int, data: dict) -> Optional[IncomeSource]:
        with self._db() as session:
            src = session.query(IncomeSource).filter(
                IncomeSource.id == income_id, IncomeSource.user_id == user_id
            ).first()
            if not src:
                return None
            for k, v in data.items():
                setattr(src, k, v)
            session.commit()
            session.refresh(src)
            return src

    def delete(self, income_id: int, user_id: int) -> bool:
        with self._db() as session:
            src = session.query(IncomeSource).filter(
                IncomeSource.id == income_id, IncomeSource.user_id == user_id
            ).first()
            if not src:
                return False
            session.delete(src)
            session.commit()
            return True

    def get_due_regular(self, user_id: int) -> List[IncomeSource]:
        today = date.today()
        with self._db() as session:
            from sqlalchemy import or_
            return session.query(IncomeSource).filter(
                IncomeSource.user_id == user_id,
                IncomeSource.is_regular == True,
                IncomeSource.is_active == True,
                or_(IncomeSource.next_date == None, IncomeSource.next_date <= today),
            ).all()
