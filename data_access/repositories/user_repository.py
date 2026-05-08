from abc import ABC, abstractmethod
from typing import List, Optional
# Импорт User из модели (предполагаем его доступность)
from models.database import User 


class IUserRepository(ABC):
    """Интерфейс репозитория для работы с пользователями."""

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Найти пользователя по email."""
        pass

    @abstractmethod
    def get_all(self) -> List[User]:
        """Получить список всех пользователей (для админа)."""
        pass

    @abstractmethod
    def create(self, user_data: dict) -> User:
        """Создать нового пользователя."""
        pass

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID."""
        pass