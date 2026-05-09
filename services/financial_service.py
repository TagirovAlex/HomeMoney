from data_access.repositories.transaction_repository import ITransactionRepository
from data_access.repositories.budget_repository import IBudgetRepository
from models.database import Transaction, Budget 
from datetime import date, timedelta

class FinancialService:
    """Сервисный слой (Use Case) для бизнес-логики финансов."""

    def __init__(self, transaction_repo: ITransactionRepository, budget_repo: IBudgetRepository):
        # Зависимости внедряются через конструктор. Это обеспечивает тестируемость.
        self.transaction_repo = transaction_repo
        self.budget_repo = budget_repo

    def add_transaction(self, user_id: int, amount: float, category_id: int, description: str = "") -> Transaction:
        """Реализовать бизнес-правила добавления транзакции и сохранить ее."""
        if amount < 0 or amount > 100000:
            raise ValueError("Недопустимый диапазон суммы для транзакции.")

        transaction_data = {
            "user_id": user_id,
            "amount": abs(amount), # Храним абсолютную сумму расхода
            "category_id": category_id,
            "description": description,
        }
        return self.transaction_repo.add_transaction(transaction_data)

    def get_monthly_summary(self, user_id: int, month: int, year: int) -> dict:
        """Получить сводку расходов/доходов за месяц (бюджет, фактические расходы)."""
        from datetime import date, timedelta
        start_date = date(year, month, 1)
        try:
            end_month = start_date + timedelta(days=32)
            end_date = (end_month.replace(day=1) - timedelta(days=1)) # Последний день месяца
        except ValueError as e:
             raise ValueError(f"Некорректный месяц или год для расчетов: {e}")


        # 1. Получаем транзакции за период
        transactions = self.transaction_repo.get_transactions_by_user(
            user_id=user_id, 
            start_date=start_date, 
            end_date=end_date
        )
        total_spent = sum(t.amount for t in transactions)

        # 2. Получаем бюджеты за этот месяц для сравнения
        budgets: List[Budget] = self.budget_repo.get_active_budgets_for_user(user_id=user_id, month=month, year=year)
        total_budget = sum(b.target_amount for b in budgets)

        return {"total_spent": total_spent, "total_budgeted": total_budget, "transactions_count": len(transactions)}

    def check_budget_exceeded(self, user_id: int, category_id: int, current_month: int, current_year: int) -> bool:
        """Проверить, превышен ли бюджет по указанной категории."""
        from datetime import date, timedelta
        start_date = date(current_year, current_month, 1)
        try:
            end_month = start_date + timedelta(days=32)
            end_date = (end_month.replace(day=1) - timedelta(days=1))
        except ValueError as e:
             raise ValueError(f"Некорректный месяц или год для расчетов бюджета: {e}")

        # 1. Получаем все транзакции за период
        all_transactions = self.transaction_repo.get_transactions_by_user(
            user_id=user_id, 
            start_date=start_date, 
            end_date=end_date
        )
        
        # Суммируем только те транзакции, которые соответствуют заданной категории
        actual_spent = sum(t.amount for t in all_transactions if t.category_id == category_id)

        # 2. Получаем активный бюджет для данной категории и периода
        budgets: List[Budget] = self.budget_repo.get_active_budgets_for_user(user_id=user_id, month=current_month, year=current_year)
        
        # Находим конкретный бюджет для данной категории
        target_budget = next((b for b in budgets if b.category_id == category_id), None)

        if target_budget is None:
            return False 

        return actual_spent > target_budget.target_amount
    
    def create_budget(self, category_id: int, target_amount: float, user_id: int) -> Budget:
        budget_data = {
            "user_id": user_id,
            "category_id": category_id,
            "target_amount": target_amount,
        }
        return self.budget_repo.create_budget(budget_data)

    def get_detailed_report(self, user_id: int, role: str, month: int, year: int) -> dict:
        """Генерирует детальный отчет по всем категориям и анализирует расходы."""
        from datetime import date, timedelta
        start_date = date(year, month, 1)
        try:
            end_month = start_date + timedelta(days=32)
            end_date = (end_month.replace(day=1) - timedelta(days=1))
        except ValueError as e:
             raise ValueError(f"Некорректный месяц или год для отчета: {e}")

        transactions = self.transaction_repo.get_transactions_by_user(
            user_id=user_id, 
            start_date=start_date, 
            end_date=end_date
        )

        report = {
            "summary": {}, # Общая сводка (как в get_monthly_summary)
            "category_spending": {} # Детализация расходов по категориям
        }
        
        total_spent = sum(t.amount for t in transactions)

        # 1. Группировка и анализ расходов по категориям
        category_map: dict[int, dict] = {}
        for budget in self.budget_repo.get_active_budgets_for_user(user_id=user_id, month=month, year=year):
            category_map[budget.category_id] = {"name": f"ID:{budget.category_id}", "total_spent": 0.0, "budget": budget.target_amount}

        for t in transactions:
            if t.category_id not in category_map:
                category_map[t.category_id] = {"name": f"ID:{t.category_id}", "total_spent": 0.0, "budget": 0.0}
            category_map[t.category_id]["total_spent"] += t.amount

        # Финальная сборка отчета
        report["summary"] = self.get_monthly_summary(user_id, month=month, year=year)
        report["detailed_spending"] = {
            cat_id: {"name": category_map[cat_id]["name"], "spent": round(category_map[cat_id]["total_spent"], 2), "budget": round(category_map[cat_id]["budget"], 2)}
            for cat_id in category_map
        }

        return report

    def get_user_transactions(self, user_id: int) -> list:
        from models.database import Category
        from utils.database_session import get_db

        transactions = self.transaction_repo.get_all_for_user(user_id)
        with get_db() as session:
            cats = {c.id: c.name for c in session.query(Category).all()}
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "amount": t.amount,
                "category_id": t.category_id,
                "category_name": cats.get(t.category_id, f"ID:{t.category_id}"),
                "description": t.description or "",
                "date": t.date.isoformat() if t.date else "",
            })
        return result