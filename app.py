from flask import Flask, jsonify, request, render_template
# Импорт рабочих классов репозиториев (Критично для устранения ошибок импорта)
from data_access.repositories.user_repository import SQLAlchemyUserRepository 
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository
from services.financial_service import FinancialService
from services.auth_service import AuthService

def create_app():
    """Фабрика приложения Flask."""
    app = Flask(__name__)
    
    # --- Инициализация и создание таблиц (Должно быть вызвано один раз!) ---
    from utils.database_session import init_db
    with app.app_context():
        init_db()

    # --- Создание зависимостей репозиториев (Инъекция) ---
    user_repo: SQLAlchemyUserRepository = SQLAlchemyUserRepository() 
    transaction_repo: SQLAlchemyTransactionRepository = SQLAlchemyTransactionRepository()
    budget_repo: SQLAlchemyBudgetRepository = SQLAlchemyBudgetRepository()

    # --- Инициализация Сервисного Слоя (Use Case) ---
    financial_service = FinancialService(
        transaction_repo=transaction_repo, 
        budget_repo=budget_repo
    )

    @app.route('/')
    def index():
        """Главный маршрут - рендеринг дашборда."""
        # Передаем контекст для шаблона (например, текущего пользователя)
        return render_template('index.html', user_id=1)

    # --- API Эндпоинты: CRUD и Отчетность ---

    @app.route('/api/v1/transactions')
    def list_transactions():
        """Тестовый эндпоинт для получения сводки транзакций."""
        user_id = 1 # Тестовый ID пользователя
        try:
            summary = financial_service.get_monthly_summary(user_id, month=5, year=2024)
            return jsonify({"status": "success", "data": summary})
        except Exception as e:
            # Логирование ошибки в продакшене обязательно
            return jsonify({"status": "error", "message": f"Ошибка сервиса при генерации сводки: {str(e)}"}), 500

    @app.route('/api/v1/user/<int:user_id>/create_transaction', methods=['POST'])
    def create_transaction_endpoint(user_id):
        """Эндпоинт для создания транзакции."""
        from flask import request 
        try:
            data = request.get_json() # Получение данных из тела запроса JSON
            if not data or 'amount' not in data or 'category_id' not in data:
                 return jsonify({"status": "error", "message": "Необходимо передать amount и category_id."}), 400

            try:
                # Вызов бизнес-логики сервиса!
                amount = float(data['amount'])
                category_id = int(data['category_id'])
                description = data.get('description', '')

                transaction = financial_service.add_transaction(user_id, amount, category_id, description)
                return jsonify({"status": "success", "message": "Транзакция добавлена.", "transaction_id": transaction.id}), 201
            except ValueError as e:
                return jsonify({"status": "error", "message": str(e)}), 400
            except Exception as e:
                # Логирование ошибки в продакшене обязательно
                return jsonify({"status": "error", "message": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        except Exception as e:
            return jsonify({"status": "error", "message": f"Критическая ошибка при обработке запроса: {str(e)}"}), 400


    @app.route('/api/v1/budgets', methods=['POST'])
    def create_budget_endpoint():
        """Эндпоинт для создания нового бюджета."""
        user_id = 1 # Тестовый ID пользователя

        try:
            data = request.get_json()
            if not data or 'category_id' not in data or 'target_amount' not in data:
                 return jsonify({"status": "error", "message": "Необходимо передать category_id и target_amount."}), 400

            try:
                budget_data = {
                    "user_id": user_id,
                    "category_id": int(data['category_id']),
                    "target_amount": float(data['target_amount']),
                }
                # Вызов сервиса для создания бюджета
                budget = financial_service.create_budget(**budget_data)
                return jsonify({"status": "success", "message": "Бюджет успешно создан.", "budget_id": budget.id}), 201

            except ValueError as e:
                return jsonify({"status": "error", "message": str(e)}), 400
            except Exception as e:
                return jsonify({"status": "error", "message": f"Внутренняя ошибка сервера при создании бюджета: {str(e)}"}), 500

        except Exception as e:
            return jsonify({"status": "error", "message": f"Критическая ошибка при обработке запроса: {str(e)}"}), 400


    @app.route('/api/v1/reports', methods=['GET'])
    def generate_report():
        """Генерация детального финансового отчета по параметрам."""
        user_id = 1 # Тестовый ID пользователя
        month = request.args.get('month')
        year = request.args.get('year')

        if not month or not year:
            return jsonify({"status": "error", "message": "Необходимо указать 'month' и 'year' в параметрах запроса."}), 400
        
        try:
            month_val = int(month)
            year_val = int(year)

            # Вызываем сервис, передавая роль для проверки прав.
            report_data = financial_service.get_detailed_report(user_id, role="User", month=month_val, year=year_val) 
            return jsonify({"status": "success", "data": report_data})

        except ValueError as e:
             return jsonify({"status": "error", "message": f"Ошибка преобразования даты: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f"Внутренняя ошибка при генерации отчета: {str(e)}"}), 500


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
        return jsonify({"status": "success", "user_id": user.id}), 201

    @app.route('/api/v1/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"status": "error", "message": "email и password обязательны"}), 400
        user = user_repo.get_by_email(data['email'])
        if not user or not AuthService.verify_password(data['password'], user.hashed_password):
            return jsonify({"status": "error", "message": "Неверный email или пароль"}), 401
        return jsonify({"status": "success", "user_id": user.id, "role": user.role})

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
    # Внимание: При запуске через Systemd (рекомендуется) этот блок игнорируется.
    try:
        app = create_app()
        print("--- Приложение запущено в режиме отладки (Debug=True). ---")
        app.run(debug=True)
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {e}")