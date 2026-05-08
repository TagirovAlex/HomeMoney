from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base 
from datetime import date # Импортируем дату для лучшей работы с сессиями

# Создаем глобальный движок и фабрику сессий (это должно быть сделано только один раз)
try:
    from config import DevelopmentConfig 
    SQLALCHEMY_DATABASE_URL = DevelopmentConfig.SQLALCHEMY_DATABASE_URI
except ModuleNotFoundError:
    print("Warning: Config not found. Using default SQLite URI.")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./home_money.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
     """Контекстный менеджер для работы с сессией."""
     db = SessionLocal()
     try:
         yield db
     finally:
         db.close()

# Создание таблиц (для инициализации БД при запуске)
def init_db():
    Base.metadata.create_all(bind=engine)