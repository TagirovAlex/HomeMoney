from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from config import Config

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False})
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def reset_engine():
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None


@contextmanager
def get_db():
    db = _get_session_local()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=_get_engine())
    _run_migrations()


def _run_migrations():
    from sqlalchemy import inspect, text
    engine = _get_engine()
    with engine.connect() as conn:
        inspector = inspect(engine)
        # categories.icon
        if 'categories' in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns('categories')]
            if 'icon' not in cols:
                conn.execute(text("ALTER TABLE categories ADD COLUMN icon VARCHAR DEFAULT ''"))
        # income_sources columns added over time
        if 'income_sources' in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns('income_sources')]
            for col_def in [
                ('amount', "ALTER TABLE income_sources ADD COLUMN amount FLOAT DEFAULT 0.0"),
                ('category_id', "ALTER TABLE income_sources ADD COLUMN category_id INTEGER DEFAULT 1"),
                ('description', "ALTER TABLE income_sources ADD COLUMN description VARCHAR DEFAULT ''"),
                ('period', "ALTER TABLE income_sources ADD COLUMN period VARCHAR DEFAULT 'monthly'"),
                ('day_of_period', "ALTER TABLE income_sources ADD COLUMN day_of_period INTEGER DEFAULT 1"),
                ('next_date', "ALTER TABLE income_sources ADD COLUMN next_date DATETIME"),
                ('is_active', "ALTER TABLE income_sources ADD COLUMN is_active BOOLEAN DEFAULT 1"),
            ]:
                if col_def[0] not in cols:
                    conn.execute(text(col_def[1]))
        # transactions.type
        if 'transactions' in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns('transactions')]
            if 'type' not in cols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN type VARCHAR DEFAULT 'expense'"))
        conn.commit()
