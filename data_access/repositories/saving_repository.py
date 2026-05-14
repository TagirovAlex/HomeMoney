from typing import List, Optional
from models.database import Saving
from utils.database_session import get_db


class SavingRepository:
    def __init__(self):
        self._db = get_db

    def get_by_user(self, user_id: int) -> List[Saving]:
        with self._db() as session:
            return session.query(Saving).filter(Saving.user_id == user_id).all()

    def get_by_id(self, saving_id: int, user_id: int) -> Optional[Saving]:
        with self._db() as session:
            return session.query(Saving).filter(
                Saving.id == saving_id, Saving.user_id == user_id
            ).first()

    def create(self, data: dict) -> Saving:
        with self._db() as session:
            obj = Saving(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def update(self, saving_id: int, user_id: int, data: dict) -> Optional[Saving]:
        with self._db() as session:
            obj = session.query(Saving).filter(
                Saving.id == saving_id, Saving.user_id == user_id
            ).first()
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            session.commit()
            session.refresh(obj)
            return obj

    def delete(self, saving_id: int, user_id: int) -> bool:
        with self._db() as session:
            obj = session.query(Saving).filter(
                Saving.id == saving_id, Saving.user_id == user_id
            ).first()
            if not obj:
                return False
            session.delete(obj)
            session.commit()
            return True
