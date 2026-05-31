import os, secrets, string
os.chdir(os.path.dirname(os.path.abspath(__file__)))

alphabet = string.ascii_letters + string.digits
ADMIN_PW = "".join(secrets.choice(alphabet) for _ in range(12))
USER_PW = "".join(secrets.choice(alphabet) for _ in range(12))
PENDING_PW = "".join(secrets.choice(alphabet) for _ in range(12))

print("⚠️  ВНИМАНИЕ: seed_demo.py для разработки/тестирования!")
print("⚠️  Никогда не запускайте этот скрипт на production-сервере.")
print()

from utils.database_session import init_db
init_db()

from data_access.repositories.user_repository import SQLAlchemyUserRepository
from data_access.repositories.category_repository import SQLAlchemyCategoryRepository
from services.auth_service import AuthService
from services.financial_service import FinancialService
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository

u = SQLAlchemyUserRepository()
tx_repo = SQLAlchemyTransactionRepository()
bg_repo = SQLAlchemyBudgetRepository()
cat_repo = SQLAlchemyCategoryRepository()
fs = FinancialService(tx_repo, bg_repo, category_repo=cat_repo)

u.create({"email":"admin@demo.com","hashed_password":AuthService.hash_password(ADMIN_PW),"role":"Admin","status":"active"})
u.create({"email":"ivan@demo.com","hashed_password":AuthService.hash_password(USER_PW),"role":"User","status":"active"})
u.create({"email":"petr@demo.com","hashed_password":AuthService.hash_password(PENDING_PW),"role":"User","status":"pending"})

cat_names = ["Продукты","Аренда","Транспорт","Связь","Развлечения","Здоровье"]
for name in cat_names:
    cat_repo.create({"name": name})

cats = {c.name: c.id for c in cat_repo.get_all()}
ivan = u.get_by_email("ivan@demo.com")
ivan_id = ivan.id if ivan else None

if ivan_id:
    tx_data = [
        ("Ашан","Продукты",3500),("Пятёрочка","Продукты",1200),("Метро","Продукты",2800),
        ("Квартплата","Аренда",15000),("Такси","Транспорт",800),("Бензин","Транспорт",3200),
        ("Билайн","Связь",600),("Кино","Развлечения",1200),("Спортзал","Здоровье",3000),
        ("Продукты","Продукты",2100),("Аптека","Здоровье",1500),
    ]
    for desc, cat_name, amt in tx_data:
        fs.add_transaction(ivan_id, amt, cats[cat_name], desc)

    fs.create_budget(user_id=ivan_id, category_id=cats["Продукты"], target_amount=15000)
    fs.create_budget(user_id=ivan_id, category_id=cats["Аренда"], target_amount=18000)
    fs.create_budget(user_id=ivan_id, category_id=cats["Транспорт"], target_amount=5000)

print("Demo data ready!")
print()
print(f"Admin:   admin@demo.com / {ADMIN_PW}")
print(f"User:    ivan@demo.com  / {USER_PW}")
print(f"Pending: petr@demo.com  / {PENDING_PW} (login blocked)")
