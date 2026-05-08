from abc import ABC, abstractmethod
from typing import List, Optional
# Импорт реальной модели и утилиты сессии
from models.database import Transaction 
from utils.database_session import get_db # Используем контекстный менеджер для сессии

class SQLAlchemyTransactionRepository(ABC):
    """Конкретная реализация репозитория транзакций с использованием SQLAlchemy."""

    def __init__(self, db=None):
        self._db = get_db() 

    # --- Реализация интерфейса ITransactionRepository ---
    
    def get_transactions_by_user(self, user_id: int, start_date=None, end_date=None) -> List[Transaction]:
        """Получить список транзакций для пользователя в заданном диапазоне дат."""
        with self._db() as session:
            query = session.query(Transaction).filter(Transaction.user_id == user_id)
            if start_date:
                query = query.filter(Transaction.date >= start_date)
            if end_date:
                query = query.filter(Transaction.date <= end_date)
            return query.all()

    def add_transaction(self, transaction_data: dict) -> Transaction:
        """Добавить новую транзакцию."""
        with self._db() as session:
            new_transaction = Transaction(**transaction_data)
            session.add(new_transaction)
            session.commit()
            session.refresh(new_transaction)
            return new_transaction

    def get_all_for_user(self, user_id: int) -> List[Transaction]:
        """Получить все транзакции для пользователя."""
        with self._db() as session:
            return session.query(Transaction).filter(Transaction.user_id == user_id).all()