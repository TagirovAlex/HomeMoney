from aiogram import Bot, Dispatcher
# Импортируем сервисный слой и репозитории для работы с ботом
from services.financial_service import FinancialService 
from data_access.repositories.user_repository import IUserRepository # Для получения данных пользователя

async def setup_bot(bot: Bot):
    """Инициализация диспетчера и регистрация обработчиков."""
    dispatcher = Dispatcher()
    # Здесь будут регистрироваться все хэндлеры (обработчики команд)
    from handlers.command_handlers import register_commands # Создадим этот файл позже
    register_commands(dispatcher)

    return dispatcher

async def main():
    """Основная асинхронная функция запуска бота."""
    # Получение экземпляров репозиториев для внедрения в сервисный слой
    # Здесь должна быть сложная логика получения DI-зависимостей от Flask/DI Container.
    # Для MVP: используем заглушки, как и в Web API.
    from data_access.repositories.user_repository import SQLAlchemyUserRepository 
    from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository 
    from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository

    # Создание экземпляров репозиториев (в реальном боте они должны работать с асинхронным пулом)
    user_repo = SQLAlchemyUserRepository()
    transaction_repo = SQLAlchemyTransactionRepository()
    budget_repo = SQLAlchemyBudgetRepository()

    # Инициализация сервиса (Use Case Layer)
    financial_service = FinancialService(
        transaction_repo=transaction_repo, 
        budget_repo=budget_repo
    )
    
    dispatcher = await setup_bot(bot) # Настраиваем обработчики

    print("Bot started. Polling for updates...")
    # Запуск бота (в продакшене через worker/supervisor)
    await dispatcher.start_polling(bot)