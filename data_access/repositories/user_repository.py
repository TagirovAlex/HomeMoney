from abc import ABC, abstractmethod
from typing import List, Optional
from models.database import User 
from utils.database_session import get_db

class IUserRepository(ABC):
    """Интерфейс репозитория для работы с пользователями."""

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_all(self, current_user_id: int, role: str) -> List[User]:
        pass

    @abstractmethod
    def create(self, user_data: dict) -> User:
        pass

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def update_status(self, user_id: int, status: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_pending(self) -> List[User]:
        pass

    @abstractmethod
    def update_telegram_id(self, user_id: int, telegram_id: str) -> Optional[User]:
        pass

    @abstractmethod
    def update_role(self, user_id: int, role: str) -> Optional[User]:
        pass

class SQLAlchemyUserRepository(IUserRepository):
    """Рабочий репозиторий пользователей с использованием SQLAlchemy."""

    def __init__(self):
        self._db = get_db

    def get_by_email(self, email: str) -> Optional[User]:
        with self._db() as session:
            return session.query(User).filter(User.email == email).first()

    def get_all(self, current_user_id: int, role: str) -> List[User]:
        with self._db() as session:
            if role != 'Admin':
                # Обычный пользователь видит только себя
                return [session.query(User).filter(User.id == current_user_id).first()]
            else:
                # Админ видит всех
                return session.query(User).all()

    def create(self, user_data: dict) -> User:
        with self._db() as session:
            new_user = User(**user_data)
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self._db() as session:
            return session.query(User).filter(User.id == user_id).first()

    def update_status(self, user_id: int, status: str) -> Optional[User]:
        with self._db() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.status = status
                session.commit()
                session.refresh(user)
            return user

    def get_pending(self) -> List[User]:
        with self._db() as session:
            return session.query(User).filter(User.status == "pending").all()

    def update_role(self, user_id: int, role: str) -> Optional[User]:
        with self._db() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.role = role
                session.commit()
                session.refresh(user)
            return user

    def update_telegram_id(self, user_id: int, telegram_id: str) -> Optional[User]:
        with self._db() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.telegram_id = telegram_id
                session.commit()
                session.refresh(user)
            return user