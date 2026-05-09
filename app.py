from flask import Flask, jsonify, request, render_template
from data_access.repositories.user_repository import SQLAlchemyUserRepository
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository
from data_access.repositories.income_repository import SQLAlchemyIncomeSourceRepository
from services.financial_service import FinancialService
from services.auth_service import AuthService, require_auth
from config import Config

def create_app():
    app = Flask(__name__)

    from utils.database_session import init_db
    with app.app_context():
        init_db()

    user_repo = SQLAlchemyUserRepository()
    transaction_repo = SQLAlchemyTransactionRepository()
    budget_repo = SQLAlchemyBudgetRepository()
    income_repo = SQLAlchemyIncomeSourceRepository()

    financial_service = FinancialService(
        transaction_repo=transaction_repo,
        budget_repo=budget_repo,
        income_repo=income_repo,
    )

    # --- Страницы ---

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/transactions')
    def transactions_page():
        return render_template('transactions.html')

    @app.route('/budgets')
    def budgets_page():
        return render_template('budgets.html')

    @app.route('/reports')
    def reports_page():
        return render_template('reports.html')

    @app.route('/admin')
    def admin_page():
        return render_template('admin.html')

    @app.route('/incomes')
    def incomes_page():
        return render_template('incomes.html')

    # --- Публичные API ---

    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "service": "Financial Management API", "version": "1.0"})

    @app.route('/api/v1/register', methods=['POST'])
    def register():
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"status": "error", "message": "email и password обязательны"}), 400
        existing = user_repo.get_by_email(data['email'])
        if existing:
            return jsonify({"status": "error", "message": "Email уже занят"}), 409
        hashed = AuthService.hash_password(data['password'])
        role = data.get("role", "User")
        user_data = {
            "email": data['email'],
            "hashed_password": hashed,
            "role": role,
            "status": "active" if role == "Admin" else "pending",
        }
        if data.get("telegram_id"):
            user_data["telegram_id"] = str(data["telegram_id"])
        user = user_repo.create(user_data)
        if user.status == "active":
            token = AuthService.create_token(user.id, user.role)
            return jsonify({"status": "success", "token": token, "user": {"id": user.id, "email": user.email, "role": user.role}}), 201
        return jsonify({"status": "success", "message": "Регистрация выполнена. Дождитесь подтверждения администратором.", "user_id": user.id}), 201

    @app.route('/api/v1/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"status": "error", "message": "email и password обязательны"}), 400
        user = user_repo.get_by_email(data['email'])
        if not user or not AuthService.verify_password(data['password'], user.hashed_password):
            return jsonify({"status": "error", "message": "Неверный email или пароль"}), 401
        if user.status == "pending":
            return jsonify({"status": "error", "message": "Аккаунт ожидает подтверждения администратором."}), 403
        if user.status == "rejected":
            return jsonify({"status": "error", "message": "Аккаунт отклонён."}), 403
        token = AuthService.create_token(user.id, user.role)
        return jsonify({"status": "success", "token": token, "user": {"id": user.id, "email": user.email, "role": user.role, "status": user.status}})

    # --- Защищённые API ---

    @app.route('/api/v1/me', methods=['GET'])
    @require_auth
    def me():
        return jsonify({"status": "success", "user": request.current_user})

    @app.route('/api/v1/transactions')
    @require_auth
    def list_transactions():
        uid = request.current_user["user_id"]
        try:
            summary = financial_service.get_monthly_summary(uid, month=5, year=2024)
            return jsonify({"status": "success", "data": summary})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Ошибка: {str(e)}"}), 500

    @app.route('/api/v1/user/<int:user_id>/create_transaction', methods=['POST'])
    @require_auth
    def create_transaction_endpoint(user_id):
        if request.current_user["user_id"] != user_id and request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Доступ запрещён"}), 403
        data = request.get_json()
        if not data or 'amount' not in data or 'category_id' not in data:
            return jsonify({"status": "error", "message": "amount и category_id обязательны"}), 400
        try:
            tx = financial_service.add_transaction(user_id, float(data['amount']), int(data['category_id']), data.get('description', ''))
            return jsonify({"status": "success", "message": "Транзакция добавлена", "transaction_id": tx.id}), 201
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/v1/user/<int:user_id>/transactions', methods=['GET'])
    @require_auth
    def user_transactions(user_id):
        if request.current_user["user_id"] != user_id and request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Доступ запрещён"}), 403
        try:
            txs = financial_service.get_user_transactions(user_id)
            return jsonify({"status": "success", "data": txs})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/v1/budgets', methods=['GET'])
    @require_auth
    def list_budgets():
        uid = request.current_user["user_id"]
        budgets = budget_repo.get_all_for_user(uid)
        from models.database import Category
        from utils.database_session import get_db
        with get_db() as session:
            cats = {c.id: c.name for c in session.query(Category).all()}
        from models.database import Category as CatModel
        with get_db() as session:
            cat_icons = {c.id: c.icon or "" for c in session.query(CatModel).all()}
        return jsonify({"status": "success", "data": [
            {"id": b.id, "category_id": b.category_id, "category_name": cats.get(b.category_id, f"ID:{b.category_id}"),
             "category_icon": cat_icons.get(b.category_id, ""),
             "target_amount": b.target_amount,
             "period_start": b.period_start_date.isoformat() if b.period_start_date else "",
             "period_end": b.period_end_date.isoformat() if b.period_end_date else ""}
            for b in budgets
        ]})

    @app.route('/api/v1/budgets', methods=['POST'])
    @require_auth
    def create_budget_endpoint():
        data = request.get_json()
        if not data or 'category_id' not in data or 'target_amount' not in data:
            return jsonify({"status": "error", "message": "category_id и target_amount обязательны"}), 400
        try:
            budget = financial_service.create_budget(
                user_id=request.current_user["user_id"],
                category_id=int(data['category_id']),
                target_amount=float(data['target_amount'])
            )
            return jsonify({"status": "success", "message": "Бюджет создан", "budget_id": budget.id}), 201
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/v1/reports', methods=['GET'])
    @require_auth
    def generate_report():
        uid = request.current_user["user_id"]
        role = request.current_user["role"]
        month = request.args.get('month')
        year = request.args.get('year')
        if not month or not year:
            return jsonify({"status": "error", "message": "Параметры month и year обязательны"}), 400
        try:
            report = financial_service.get_detailed_report(uid, role=role, month=int(month), year=int(year))
            return jsonify({"status": "success", "data": report})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/v1/backup', methods=['GET'])
    @require_auth
    def backup_api():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        from utils.backup_service import BackupService
        svc = BackupService()
        result = svc.create_backup(request.args.get('type', 'full'))
        ok = "Ошибка" not in result
        return jsonify({"status": "success" if ok else "error", "message": result})

    @app.route('/api/v1/users', methods=['GET'])
    @require_auth
    def list_users():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        users = user_repo.get_all(request.current_user["user_id"], request.current_user["role"])
        return jsonify({"status": "success", "data": [{"id": u.id, "email": u.email, "role": u.role, "status": u.status, "telegram_id": u.telegram_id} for u in users]})

    @app.route('/api/v1/users/pending', methods=['GET'])
    @require_auth
    def pending_users():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        users = user_repo.get_pending()
        return jsonify({"status": "success", "data": [{"id": u.id, "email": u.email, "telegram_id": u.telegram_id} for u in users]})

    @app.route('/api/v1/users/<int:user_id>/approve', methods=['POST'])
    @require_auth
    def approve_user(user_id):
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        user = user_repo.update_status(user_id, "active")
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        return jsonify({"status": "success", "message": f"Пользователь {user.email} подтверждён"})

    @app.route('/api/v1/users/<int:user_id>/reject', methods=['POST'])
    @require_auth
    def reject_user(user_id):
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        user = user_repo.update_status(user_id, "rejected")
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        return jsonify({"status": "success", "message": f"Пользователь {user.email} отклонён"})

    @app.route('/api/v1/categories', methods=['GET', 'POST'])
    @require_auth
    def categories_api():
        from models.database import Category
        from utils.database_session import get_db
        if request.method == 'GET':
            with get_db() as session:
                cats = session.query(Category).all()
            return jsonify({"status": "success", "data": [{"id": c.id, "name": c.name, "description": c.description or "", "icon": c.icon or ""} for c in cats]})
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "name обязателен"}), 400
        with get_db() as session:
            cat = Category(name=data['name'], description=data.get('description', ''), icon=data.get('icon', ''))
            session.add(cat)
            session.commit()
            session.refresh(cat)
        return jsonify({"status": "success", "category_id": cat.id}), 201

    @app.route('/api/v1/categories/<int:cat_id>', methods=['PUT'])
    @require_auth
    def update_category(cat_id):
        from models.database import Category
        from utils.database_session import get_db
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных"}), 400
        with get_db() as session:
            cat = session.query(Category).filter(Category.id == cat_id).first()
            if not cat:
                return jsonify({"status": "error", "message": "Категория не найдена"}), 404
            if 'name' in data:
                cat.name = data['name']
            if 'description' in data:
                cat.description = data['description']
            if 'icon' in data:
                cat.icon = data['icon']
            session.commit()
        return jsonify({"status": "success", "message": "Категория обновлена"})

    @app.route('/api/v1/categories/<int:cat_id>', methods=['DELETE'])
    @require_auth
    def delete_category(cat_id):
        from models.database import Category
        from utils.database_session import get_db
        with get_db() as session:
            cat = session.query(Category).filter(Category.id == cat_id).first()
            if not cat:
                return jsonify({"status": "error", "message": "Категория не найдена"}), 404
            session.delete(cat)
            session.commit()
        return jsonify({"status": "success", "message": "Категория удалена"})

    @app.route('/api/v1/incomes', methods=['GET'])
    @require_auth
    def list_incomes():
        uid = request.current_user["user_id"]
        srcs = income_repo.get_by_user(uid)
        return jsonify({"status": "success", "data": [{
            "id": s.id, "name": s.name, "is_regular": s.is_regular,
            "amount": s.amount, "category_id": s.category_id,
            "description": s.description or "", "period": s.period,
            "day_of_period": s.day_of_period,
            "next_date": s.next_date.isoformat() if s.next_date else None,
            "is_active": s.is_active,
        } for s in srcs]})

    @app.route('/api/v1/incomes', methods=['POST'])
    @require_auth
    def create_income():
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "name обязателен"}), 400
        from datetime import date
        rec = {
            "user_id": request.current_user["user_id"],
            "name": data['name'],
            "is_regular": data.get('is_regular', True),
            "amount": float(data.get('amount', 0)),
            "category_id": int(data.get('category_id', 1)),
            "description": data.get('description', ''),
            "period": data.get('period', 'monthly'),
            "day_of_period": int(data.get('day_of_period', 1)),
        }
        if rec["is_regular"]:
            rec["next_date"] = date.today()
        src = income_repo.create(rec)
        return jsonify({"status": "success", "income_id": src.id}), 201

    @app.route('/api/v1/incomes/<int:income_id>', methods=['PUT'])
    @require_auth
    def update_income(income_id):
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных"}), 400
        allowed = {"name", "is_regular", "amount", "category_id", "description", "period", "day_of_period", "next_date", "is_active"}
        update = {}
        for k in allowed:
            if k in data:
                v = data[k]
                if k in ("amount",): v = float(v)
                if k in ("category_id", "day_of_period"): v = int(v)
                update[k] = v
        src = income_repo.update(income_id, request.current_user["user_id"], update)
        if not src:
            return jsonify({"status": "error", "message": "Источник дохода не найден"}), 404
        return jsonify({"status": "success", "message": "Источник дохода обновлён"})

    @app.route('/api/v1/incomes/<int:income_id>', methods=['DELETE'])
    @require_auth
    def delete_income(income_id):
        ok = income_repo.delete(income_id, request.current_user["user_id"])
        if not ok:
            return jsonify({"status": "error", "message": "Источник дохода не найден"}), 404
        return jsonify({"status": "success", "message": "Источник дохода удалён"})

    @app.route('/api/v1/incomes/process', methods=['POST'])
    @require_auth
    def process_regular_incomes():
        uid = request.current_user["user_id"]
        result = financial_service.process_regular_payments(uid)
        return jsonify({"status": "success", "data": result})

    @app.route('/api/v1/admin/settings', methods=['GET', 'PUT'])
    @require_auth
    def admin_settings():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        from utils.env_manager import get_settings, update_settings
        if request.method == 'GET':
            s = get_settings()
            return jsonify({"status": "success", "data": {
                "HM_BOT_TOKEN": s.get("HM_BOT_TOKEN", ""),
                "HM_BOT_PROXY_URL": s.get("HM_BOT_PROXY_URL", ""),
                "HM_BOT_ALLOWED_USERS": s.get("HM_BOT_ALLOWED_USERS", ""),
                "HM_DEBUG": s.get("HM_DEBUG", "true"),
            }})
        data = request.get_json()
        allowed = {"HM_BOT_TOKEN", "HM_BOT_PROXY_URL", "HM_BOT_ALLOWED_USERS", "HM_DEBUG"}
        updates = {k: str(v) for k, v in data.items() if k in allowed}
        if not updates:
            return jsonify({"status": "error", "message": "Нет допустимых полей"}), 400
        errors = update_settings(updates)
        if errors:
            return jsonify({"status": "error", "message": "; ".join(errors)}), 500
        return jsonify({"status": "success", "message": "Настройки сохранены. Перезапустите бота/сервер для применения."})

    # --- Error handlers ---

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', code=403, message="Доступ запрещён"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404, message="Страница не найдена"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', code=500, message="Внутренняя ошибка сервера"), 500

    return app

if __name__ == '__main__':
    try:
        app = create_app()
        print(f"--- HomeMoney запущен (Debug={Config.DEBUG}) ---")
        app.run(debug=Config.DEBUG)
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
