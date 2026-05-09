from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base

# --- Глобальные настройки SQLAlchemy (Для максимальной простоты и переносимости) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./home_money.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """Контекстный менеджер для работы с сессией."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Создает все таблицы в базе данных SQLite."""
    Base.metadata.create_all(bind=engine)