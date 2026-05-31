from abc import ABC, abstractmethod
from typing import List, Optional
from models.database import Category
from utils.database_session import get_db


class ICategoryRepository(ABC):

    @abstractmethod
    def get_by_id(self, category_id: int) -> Optional[Category]:
        pass

    @abstractmethod
    def get_all(self) -> List[Category]:
        pass

    @abstractmethod
    def create(self, data: dict) -> Category:
        pass

    @abstractmethod
    def update(self, category_id: int, data: dict) -> Optional[Category]:
        pass

    @abstractmethod
    def delete(self, category_id: int) -> bool:
        pass


class SQLAlchemyCategoryRepository(ICategoryRepository):
    def __init__(self):
        self._db = get_db

    def get_by_id(self, category_id: int) -> Optional[Category]:
        with self._db() as session:
            return session.query(Category).filter(Category.id == category_id).first()

    def get_all(self) -> List[Category]:
        with self._db() as session:
            return session.query(Category).all()

    def create(self, data: dict) -> Category:
        with self._db() as session:
            obj = Category(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def update(self, category_id: int, data: dict) -> Optional[Category]:
        with self._db() as session:
            obj = session.query(Category).filter(Category.id == category_id).first()
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            session.commit()
            return obj

    def delete(self, category_id: int) -> bool:
        with self._db() as session:
            obj = session.query(Category).filter(Category.id == category_id).first()
            if not obj:
                return False
            session.delete(obj)
            session.commit()
            return True
