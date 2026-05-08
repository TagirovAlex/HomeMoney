from data_access.repositories.transaction_repository import ITransactionRepository # Импортируем конкретный репозиторий
# ... (остальной код остается без изменений)
    def __init__(self, transaction_repo: ITransactionRepository, budget_repo: IBudgetRepository):
        self.transaction_repo = transaction_repo
        self.budget_repo = budget_repo

    def add_transaction(self, user_id: int, amount: float, category_id: int, description: str = "") -> 'Transaction':
        """Реализовать бизнес-правила добавления транзакции и сохранить ее."""
        # 1. Проверка бизнес-логики (например, сумма не должна быть отрицательной)
        if amount < 0:
            raise ValueError("Сумма расхода не может быть отрицательной при добавлении.") # Предполагаем положительную сумму для расходов

        # 2. Вызов репозитория
        transaction_data = {
            "user_id": user_id,
            "amount": abs(amount), # Убедимся, что сумма всегда позитивна в базе и определяется типом транзакции
            "category_id": category_id,
            "description": description
        }
        return self.transaction_repo.add_transaction(transaction_data)

    def get_monthly_summary(self, user_id: int, month: int, year: int) -> dict:
        """Получить сводку расходов/доходов за месяц (бюджет, фактические расходы)."""
        # 1. Получаем все транзакции за период
        transactions = self.transaction_repo.get_transactions_by_user(user_id=user_id) # Нужно доработать поиск по дате в репо

        total_spent = sum(t.amount for t in transactions)
        return {"total_spent": total_spent, "budgeted": 0} # Временно возвращаем заглушку

    def check_budget_exceeded(self, user_id: int, category_id: int, current_month: int, current_year: int) -> bool:
        """Проверить, превышен ли бюджет по указанной категории."""
        budgets = self.budget_repo.get_active_budgets_for_user(user_id, month=current_month, year=current_year)
        # Логика сравнения фактических расходов с бюджетами
        return False # Временно заглушка