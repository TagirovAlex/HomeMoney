import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("⚠️  ВНИМАНИЕ: seed_demo.py создаёт тестовые аккаунты со слабыми паролями!")
print("⚠️  Никогда не запускайте этот скрипт на production-сервере.")
print()

from utils.database_session import init_db
init_db()

from data_access.repositories.user_repository import SQLAlchemyUserRepository
from services.auth_service import AuthService
from services.financial_service import FinancialService
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository
from models.database import Category
from utils.database_session import get_db

u = SQLAlchemyUserRepository()
tx = SQLAlchemyTransactionRepository()
bg = SQLAlchemyBudgetRepository()
fs = FinancialService(tx, bg)

u.create({"email":"admin@demo.com","hashed_password":AuthService.hash_password("admin"),"role":"Admin","status":"active"})
u.create({"email":"ivan@demo.com","hashed_password":AuthService.hash_password("123"),"role":"User","status":"active"})
u.create({"email":"petr@demo.com","hashed_password":AuthService.hash_password("123"),"role":"User","status":"pending"})

with get_db() as s:
    for name in ["Продукты","Аренда","Транспорт","Связь","Развлечения","Здоровье"]:
        s.add(Category(name=name))
    s.commit()

for desc, cat, amt in [
    ("Ашан",1,3500),("Пятёрочка",1,1200),("Метро",1,2800),
    ("Квартплата",2,15000),("Такси",3,800),("Бензин",3,3200),
    ("Билайн",4,600),("Кино",5,1200),("Спортзал",6,3000),
    ("Продукты",1,2100),("Аптека",6,1500),
]:
    fs.add_transaction(2, amt, cat, desc)

fs.create_budget(user_id=2, category_id=1, target_amount=15000)
fs.create_budget(user_id=2, category_id=2, target_amount=18000)
fs.create_budget(user_id=2, category_id=3, target_amount=5000)

print("Demo data ready!")
print()
print("Admin: admin@demo.com / admin")
print("User:  ivan@demo.com  / 123")
print("Pending: petr@demo.com / 123 (login blocked)")
