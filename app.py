from flask import Flask, jsonify, request, render_template
from data_access.repositories.user_repository import SQLAlchemyUserRepository
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository
from services.financial_service import FinancialService
from services.auth_service import AuthService, require_auth

def create_app():
    app = Flask(__name__)

    from utils.database_session import init_db
    with app.app_context():
        init_db()

    user_repo = SQLAlchemyUserRepository()
    transaction_repo = SQLAlchemyTransactionRepository()
    budget_repo = SQLAlchemyBudgetRepository()

    financial_service = FinancialService(
        transaction_repo=transaction_repo,
        budget_repo=budget_repo
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
        user = user_repo.create({"email": data['email'], "hashed_password": hashed, "role": data.get("role", "User")})
        token = AuthService.create_token(user.id, user.role)
        return jsonify({"status": "success", "token": token, "user": {"id": user.id, "email": user.email, "role": user.role}}), 201

    @app.route('/api/v1/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"status": "error", "message": "email и password обязательны"}), 400
        user = user_repo.get_by_email(data['email'])
        if not user or not AuthService.verify_password(data['password'], user.hashed_password):
            return jsonify({"status": "error", "message": "Неверный email или пароль"}), 401
        token = AuthService.create_token(user.id, user.role)
        return jsonify({"status": "success", "token": token, "user": {"id": user.id, "email": user.email, "role": user.role}})

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
        return jsonify({"status": "success", "data": [{"id": u.id, "email": u.email, "role": u.role} for u in users]})

    @app.route('/api/v1/categories', methods=['GET', 'POST'])
    @require_auth
    def categories_api():
        from models.database import Category
        from utils.database_session import get_db
        if request.method == 'GET':
            with get_db() as session:
                cats = session.query(Category).all()
            return jsonify({"status": "success", "data": [{"id": c.id, "name": c.name, "description": c.description} for c in cats]})
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "name обязателен"}), 400
        with get_db() as session:
            cat = Category(name=data['name'], description=data.get('description', ''))
            session.add(cat)
            session.commit()
            session.refresh(cat)
        return jsonify({"status": "success", "category_id": cat.id}), 201

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
        print("--- HomeMoney запущен (Debug=True) ---")
        app.run(debug=True)
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
