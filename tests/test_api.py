import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

@pytest.fixture
def app():
    from config import Config
    Config.SECRET_KEY = "test-secret-key"
    Config.DATABASE_URL = "sqlite:///:memory:"
    from utils.database_session import reset_engine, init_db
    reset_engine()
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        init_db()
        from utils.database_session import get_db
        from models.database import User, Category
        with get_db() as session:
            from services.auth_service import AuthService
            admin = User(email="admin@test.com", hashed_password=AuthService.hash_password("admin"), role="Admin", status="active")
            user = User(email="user@test.com", hashed_password=AuthService.hash_password("user"), role="User", status="active")
            session.add_all([admin, user])
            session.commit()
            cat = Category(name="Food", description="Groceries")
            session.add(cat)
            session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def auth_token(client, email, password):
    r = client.post("/api/v1/login", json={"email": email, "password": password})
    return r.get_json()["token"]

class TestPublicAPI:
    def test_health(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "ok"

    def test_register(self, client):
        r = client.post("/api/v1/register", json={"email": "new@test.com", "password": "pass"})
        assert r.status_code == 201
        d = r.get_json()
        assert d["status"] == "success"

    def test_login_success(self, client):
        r = client.post("/api/v1/login", json={"email": "admin@test.com", "password": "admin"})
        assert r.status_code == 200
        assert "token" in r.get_json()

    def test_login_fail(self, client):
        r = client.post("/api/v1/login", json={"email": "admin@test.com", "password": "wrong"})
        assert r.status_code == 401

class TestAuthProtectedAPI:
    def test_me(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.get_json()["user"]["role"] == "Admin"

    def test_me_unauthorized(self, client):
        r = client.get("/api/v1/me")
        assert r.status_code == 401

    def test_transactions_list(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/transactions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_create_transaction(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/user/2/create_transaction",
            json={"amount": 150.0, "category_id": 1, "description": "test"},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201

    def test_user_transactions(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.get("/api/v1/user/2/transactions",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "success"

    def test_categories_list(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/categories", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_incomes_list(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.get("/api/v1/incomes", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_create_income(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/incomes",
            json={"name": "Salary", "is_regular": True},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201

    def test_budgets_list(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/budgets", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_create_budget(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/budgets",
            json={"category_id": 1, "target_amount": 5000.0},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201

    def test_report(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/reports?month=5&year=2024",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_transactions_with_filters(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.get("/api/v1/user/2/transactions?month=5&year=2024&category_id=1&page=1&limit=10",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "success"
        assert "total" in d
        assert "page" in d
        assert "limit" in d
        assert d["page"] == 1

    def test_create_category(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/categories",
            json={"name": "TestCat", "icon": "📁", "description": "test"},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        assert r.get_json()["status"] == "success"

    def test_update_category(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.put("/api/v1/categories/1",
            json={"name": "UpdatedFood", "icon": "🍎"},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.get_json()["status"] == "success"

    def test_delete_category(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.delete("/api/v1/categories/1",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_update_budget(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/budgets",
            json={"category_id": 1, "target_amount": 5000.0},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        bid = r.get_json()["budget_id"]
        r = client.put(f"/api/v1/budgets/{bid}",
            json={"target_amount": 8000.0},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_delete_budget(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/budgets",
            json={"category_id": 1, "target_amount": 3000.0},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        bid = r.get_json()["budget_id"]
        r = client.delete(f"/api/v1/budgets/{bid}",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_update_income(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/incomes",
            json={"name": "Bonus", "amount": 5000, "is_regular": True},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        iid = r.get_json()["income_id"]
        r = client.put(f"/api/v1/incomes/{iid}",
            json={"amount": 7000},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_delete_income(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/incomes",
            json={"name": "Temp", "amount": 1000, "is_regular": True},
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        iid = r.get_json()["income_id"]
        r = client.delete(f"/api/v1/incomes/{iid}",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_process_incomes(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.post("/api/v1/incomes/process",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "success"
        assert "processed" in d["data"]

    def test_categories_page(self, client):
        r = client.get("/categories")
        assert r.status_code == 200

    def test_report_no_params_returns_400(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/reports",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 400

class TestAdminAPI:
    def test_list_users(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_non_admin_cannot_list_users(self, client):
        token = auth_token(client, "user@test.com", "user")
        r = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_backup(self, client):
        token = auth_token(client, "admin@test.com", "admin")
        r = client.get("/api/v1/backup?type=json", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

def test_pages_render(client):
    pages = ["/login", "/", "/transactions", "/incomes", "/budgets", "/reports"]
    for page in pages:
        r = client.get(page)
        assert r.status_code == 200, f"Page {page} returned {r.status_code}"

def test_admin_page_redirects(client):
    r = client.get("/admin")
    assert r.status_code == 200
