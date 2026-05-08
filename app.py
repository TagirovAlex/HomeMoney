from flask import Flask, jsonify
from data_access.repositories.user_repository import IUserRepository, SQLAlchemyUserRepository
from data_access.repositories.transaction_repository import ITransactionRepository, SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import IBudgetRepository, SQLAlchemyBudgetRepository
from services.financial_service import FinancialService
from utils.database_session import init_db # Используем функцию инициализации БД

def create_app():
    """Фабрика приложения Flask."""
    app = Flask(__name__)
    # 1. Инициализация и создание таблиц (это нужно сделать один раз!)
    init_db() 
    
    # --- Создание зависимостей репозиториев ---
    # В реальном проекте здесь используется DI Container, а не прямое new upcasting.
    user_repo: IUserRepository = SQLAlchemyUserRepository(db=None) # Передаем сессию через контекст
    transaction_repo: ITransactionRepository = SQLAlchemyTransactionRepository(db=None)
    budget_repo: IBudgetRepository = SQLAlchemyBudgetRepository(db=None)

    # --- Инициализация Сервисного Слоя (Use Case) ---
    financial_service = FinancialService(
        transaction_repo=transaction_repo, 
        budget_repo=budget_repo
    )

    @app.route('/api/v1/transactions')
    def list_transactions():
        """Тестовый эндпоинт для получения транзакций и сводки."""
        user_id = 1 # В реальной жизни берется из контекста пользователя (после аутентификации)
        try:
            summary = financial_service.get_monthly_summary(user_id, month=5, year=2024)
            return jsonify({"status": "success", "data": summary})
        except Exception as e:
            # Логирование ошибки в продакшене обязательно
            return jsonify({"status": "error", "message": f"Ошибка сервиса: {str(e)}"}), 500

    @app.route('/api/v1/user/<int:user_id>/create_transaction', methods=['POST'])
    def create_transaction_endpoint(user_id):
        """Эндпоинт для создания транзакции."""
        from flask import request # Импорт запроса, нужен для тестирования
        try:
            data = request.json
            amount = float(data['amount'])
            category_id = int(data['category_id'])
            description = data.get('description', '')

            transaction = financial_service.add_transaction(user_id, amount, category_id, description)
            return jsonify({"status": "success", "message": "Транзакция добавлена.", "transaction_id": transaction.id}), 201
        except (ValueError, TypeError) as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f"Внутренняя ошибка сервера: {str(e)}"}), 500


    # Добавляем базовый роут для проверки доступности системы
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "service": "Financial Management API", "version": "1.0"})

    return app

if __name__ == '__main__':
    # Проверяем наличие зависимостей и запускаем приложение только после их установки
    try:
        app = create_app()
        print("--- Приложение запущено в режиме отладки (Debug=True). ---")
        app.run(debug=True)
    except Exception as e:
        print(f"Ошибка при инициализации приложения. Убедитесь, что вы установили зависимости и выполнили миграции БД: {e}")