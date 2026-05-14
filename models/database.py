from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default='User') # Admin or User
    status = Column(String, default='active') # pending, active, rejected
    telegram_id = Column(String, default='')

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    icon = Column(String, default='')
    type = Column(String, default='expense')  # 'expense' or 'income'

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    category_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String)
    date = Column(DateTime, default=datetime.utcnow)
    type = Column(String, default='expense')  # 'expense' or 'income'

class Budget(Base):
    __tablename__ = 'budgets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    category_id = Column(Integer, nullable=False)
    target_amount = Column(Float, nullable=False)
    period_start_date = Column(DateTime, default=datetime.utcnow)
    period_end_date = Column(DateTime)

class IncomeSource(Base):
    __tablename__ = 'income_sources'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    is_regular = Column(Boolean, default=True)
    amount = Column(Float, default=0.0)
    category_id = Column(Integer, default=1)
    description = Column(String, default='')
    period = Column(String, default='monthly')
    day_of_period = Column(Integer, default=1)
    next_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

class Saving(Base):
    __tablename__ = 'savings'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    amount = Column(Float, default=0.0)
    type = Column(String, default='deposit')  # deposit, stocks, bonds, cash, other
    description = Column(String, default='')
    created_at = Column(DateTime, default=datetime.utcnow)