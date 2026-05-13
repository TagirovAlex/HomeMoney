from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from datetime import datetime
from calendar import monthrange
from models.database import Transaction 
from utils.database_session import get_db # Используем контекстный менеджер для сессии

class ITransactionRepository(ABC):
    """Интерфейс репозитория для работы с финансовыми транзакциями."""

    @abstractmethod
    def get_transactions_by_user(self, user_id: int, start_date=None, end_date=None) -> List[Transaction]:
        pass

    @abstractmethod
    def add_transaction(self, transaction_data: dict) -> Transaction:
        pass

    @abstractmethod
    def get_all_for_user(self, user_id: int) -> List[Transaction]:
        pass

    @abstractmethod
    def get_filtered_for_user(self, user_id: int, month: int = None, year: int = None, category_id: int = None, page: int = 1, limit: int = 50) -> Tuple[List[Transaction], int]:
        pass

class SQLAlchemyTransactionRepository:
    """Рабочий репозиторий транзакций с использованием SQLAlchemy."""

    def __init__(self):
        self._db = get_db

    # --- Реализация ITransactionRepository ---
    
    def get_transactions_by_user(self, user_id: int, start_date=None, end_date=None) -> List[Transaction]:
        with self._db() as session:
            query = session.query(Transaction).filter(Transaction.user_id == user_id)
            if start_date:
                query = query.filter(Transaction.date >= start_date)
            if end_date:
                query = query.filter(Transaction.date <= end_date)
            return query.all()

    def add_transaction(self, transaction_data: dict) -> Transaction:
        with self._db() as session:
            new_transaction = Transaction(**transaction_data)
            session.add(new_transaction)
            session.commit()
            session.refresh(new_transaction)
            return new_transaction

    def get_all_for_user(self, user_id: int) -> List[Transaction]:
        with self._db() as session:
            return session.query(Transaction).filter(Transaction.user_id == user_id).all()

    def get_filtered_for_user(self, user_id: int, month: int = None, year: int = None, category_id: int = None, page: int = 1, limit: int = 50) -> Tuple[List[Transaction], int]:
        with self._db() as session:
            query = session.query(Transaction).filter(Transaction.user_id == user_id)
            if month and year:
                start = datetime(year, month, 1)
                _, last_day = monthrange(year, month)
                end = datetime(year, month, last_day, 23, 59, 59)
                query = query.filter(Transaction.date >= start, Transaction.date <= end)
            elif year and not month:
                start = datetime(year, 1, 1)
                end = datetime(year, 12, 31, 23, 59, 59)
                query = query.filter(Transaction.date >= start, Transaction.date <= end)
            if category_id:
                query = query.filter(Transaction.category_id == category_id)
            total = query.count()
            query = query.order_by(Transaction.date.desc()).offset((page - 1) * limit).limit(limit)
            return query.all(), total

    def update_transaction(self, tx_id: int, user_id: int, data: dict) -> Optional[Transaction]:
        with self._db() as session:
            tx = session.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user_id).first()
            if not tx:
                return None
            for k, v in data.items():
                if hasattr(tx, k):
                    setattr(tx, k, v)
            session.commit()
            session.refresh(tx)
            return tx