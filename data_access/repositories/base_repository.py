from abc import ABC, abstractmethod
from typing import List, Optional

class IBaseRepository(ABC):
    """Базовый абстрактный класс для всех репозиториев."""

    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional['Model']:
        """Получить объект по уникальному ID."""
        pass

    @abstractmethod
    def add(self, item: 'Model') -> None:
        """Добавить новый объект."""
        pass

    @abstractmethod
    def update(self, item: 'Model') -> None:
        """Обновить существующий объект."""
        pass

    @abstractmethod
    def delete(self, item_id: int) -> bool:
        """Удалить объект по ID. Возвращает True в случае успеха."""
        pass