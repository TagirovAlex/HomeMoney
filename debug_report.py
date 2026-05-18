import sys
sys.path.insert(0, '.')
from utils.database_session import get_db
from models.database import Transaction, User, Category
from datetime import date, datetime, timedelta

print('=== ALL TRANSACTIONS IN DB ===')
with get_db() as s:
    txs = s.query(Transaction).order_by(Transaction.date).all()
    for t in txs:
        u = s.query(User).filter(User.id == t.user_id).first()
        cat = s.query(Category).filter(Category.id == t.category_id).first()
        print('  tx_id=%s, user=%s, amount=%s, cat=%s(%s), date=%s, type=%s' % (
            t.id, u.email if u else '?', t.amount,
            cat.name if cat else '?', t.category_id,
            repr(t.date), t.type))

    print()
    print('=== April 2026: date range (date objects) ===')
    start = date(2026, 4, 1)
    end_month = start + timedelta(days=32)
    end = end_month.replace(day=1) - timedelta(days=1)
    print('  start=%s, end=%s' % (start, end))
    txs_apr = s.query(Transaction).filter(
        Transaction.date >= start,
        Transaction.date <= end
    ).all()
    print('  Found: %d' % len(txs_apr))
    for t in txs_apr:
        print('    tx_id=%s amount=%s date=%s' % (t.id, t.amount, t.date))

    print()
    print('=== April 2026: datetime range ===')
    start_dt = datetime(2026, 4, 1, 0, 0, 0)
    end_dt = datetime(2026, 4, 30, 23, 59, 59)
    txs_apr2 = s.query(Transaction).filter(
        Transaction.date >= start_dt,
        Transaction.date <= end_dt
    ).all()
    print('  Found: %d' % len(txs_apr2))
    for t in txs_apr2:
        print('    tx_id=%s amount=%s date=%s' % (t.id, t.amount, t.date))
