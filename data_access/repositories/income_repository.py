from abc import ABC, abstractmethod
from typing import List, Optional
from models.database import IncomeSource
from utils.database_session import get_db

class IIncomeSourceRepository(ABC):
    @abstractmethod
    def get_by_user(self, user_id: int) -> List[IncomeSource]:
        pass

    @abstractmethod
    def create(self, data: dict) -> IncomeSource:
        pass

    @abstractmethod
    def delete(self, income_id: int, user_id: int) -> bool:
        pass

class SQLAlchemyIncomeSourceRepository:
    def __init__(self):
        self._db = get_db

    def get_by_user(self, user_id: int) -> List[IncomeSource]:
        with self._db() as session:
            return session.query(IncomeSource).filter(IncomeSource.user_id == user_id).all()

    def create(self, data: dict) -> IncomeSource:
        with self._db() as session:
            src = IncomeSource(**data)
            session.add(src)
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
