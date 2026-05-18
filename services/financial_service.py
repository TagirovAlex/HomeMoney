from typing import Optional
from data_access.repositories.transaction_repository import ITransactionRepository
from data_access.repositories.budget_repository import IBudgetRepository
from data_access.repositories.income_repository import IIncomeSourceRepository
from models.database import Transaction, Budget
from datetime import date, timedelta
from calendar import monthrange

class FinancialService:
    """Сервисный слой (Use Case) для бизнес-логики финансов."""

    def __init__(self, transaction_repo: ITransactionRepository, budget_repo: IBudgetRepository, income_repo: IIncomeSourceRepository = None):
        # Зависимости внедряются через конструктор. Это обеспечивает тестируемость.
        self.transaction_repo = transaction_repo
        self.budget_repo = budget_repo
        self.income_repo = income_repo

    def add_transaction(self, user_id: int, amount: float, category_id: int, description: str = "", date=None) -> Transaction:
        """Добавить транзакцию. Тип (расход/доход) определяется из категории."""
        if amount < 0:
            raise ValueError("Сумма должна быть положительным числом")
        if len(description) > 500:
            raise ValueError("Описание не может быть длиннее 500 символов")

        from models.database import Category
        from utils.database_session import get_db
        with get_db() as s:
            cat = s.query(Category).filter(Category.id == category_id).first()
            tx_type = cat.type if cat else "expense"

        from datetime import datetime
        transaction_data = {
            "user_id": user_id,
            "amount": abs(amount),
            "category_id": category_id,
            "description": description,
            "type": tx_type,
        }
        if date:
            if isinstance(date, str):
                from datetime import datetime
                date = datetime.strptime(date, "%Y-%m-%d")
            transaction_data["date"] = date
        return self.transaction_repo.add_transaction(transaction_data)

    def get_monthly_summary(self, user_id: int, month: int, year: int) -> dict:
        """Получить сводку расходов/доходов за месяц (бюджет, фактические расходы)."""
        from datetime import date, timedelta, datetime
        start_date = date(year, month, 1)
        try:
            end_month = start_date + timedelta(days=32)
            end_date = end_month.replace(day=1)  # Первый день следующего месяца
        except ValueError as e:
             raise ValueError(f"Некорректный месяц или год для расчетов: {e}")


        # 1. Получаем транзакции за период
        transactions = self.transaction_repo.get_transactions_by_user(
            user_id=user_id, 
            start_date=start_date, 
            end_date=end_date
        )
        from models.database import Category
        from utils.database_session import get_db
        with get_db() as s:
            cat_types = {c.id: c.type for c in s.query(Category).all()}
        total_income = sum(t.amount for t in transactions if cat_types.get(t.category_id, getattr(t, 'type', 'expense')) == 'income')
        total_spent = sum(t.amount for t in transactions if cat_types.get(t.category_id, getattr(t, 'type', 'expense')) == 'expense')

        # 2. Получаем бюджеты за этот месяц для сравнения
        budgets: List[Budget] = self.budget_repo.get_active_budgets_for_user(user_id=user_id, month=month, year=year)
        total_budget = sum(b.target_amount for b in budgets)

        return {
            "total_income": total_income,
            "total_spent": total_spent,
            "total_budgeted": total_budget,
            "transactions_count": len(transactions),
        }

    def check_budget_exceeded(self, user_id: int, category_id: int, current_month: int, current_year: int) -> bool:
        """Проверить, превышен ли бюджет по указанной категории."""
        from datetime import date, timedelta
        start_date = date(current_year, current_month, 1)
        try:
            end_month = start_date + timedelta(days=32)
            end_date = end_month.replace(day=1)  # Первый день следующего месяца
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
        """Генерирует детальный отчет с остатками и оборотами."""
        from datetime import date, timedelta, datetime
        start_date = date(year, month, 1)
        try:
            end_month = start_date + timedelta(days=32)
            end_date = end_month.replace(day=1)  # Первый день следующего месяца
        except ValueError as e:
             raise ValueError(f"Некорректный месяц или год для отчета: {e}")

        transactions = self.transaction_repo.get_transactions_by_user(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        # Все транзакции до начала периода (для начального остатка)
        prev_transactions = self.transaction_repo.get_transactions_by_user(
            user_id=user_id,
            end_date=start_date  # < start_date — все до первого дня месяца
        )

        import logging
        logging.getLogger('report').info(
            'get_detailed_report uid=%s month=%s year=%s: range=[%s, %s], '
            'txs_found=%s (period), prev_found=%s (before)',
            user_id, month, year, start_date, end_date,
            len(transactions), len(prev_transactions))

        report = {
            "summary": {},
            "category_spending": {}
        }

        # Определяем тип категорий (expense/income)
        from models.database import Category
        from utils.database_session import get_db
        with get_db() as session:
            cat_types = {c.id: c.type for c in session.query(Category).all()}

        def _is_income(t):
            return cat_types.get(t.category_id, 'expense') == 'income'

        # Обороты за период
        total_income = sum(t.amount for t in transactions if _is_income(t))
        total_expense = sum(t.amount for t in transactions if not _is_income(t))

        # Начальный остаток (все доходы до периода - все расходы до периода)
        opening_balance = (
            sum(t.amount for t in prev_transactions if _is_income(t)) -
            sum(t.amount for t in prev_transactions if not _is_income(t))
        )

        closing_balance = opening_balance + total_income - total_expense

        # Группировка расходов по категориям (только расходные транзакции)
        from models.database import Category
        from utils.database_session import get_db
        with get_db() as session:
            cat_info = {c.id: {"name": c.name, "icon": c.icon or ""} for c in session.query(Category).all()}

        category_map: dict[int, dict] = {}
        for budget in self.budget_repo.get_active_budgets_for_user(user_id=user_id, month=month, year=year):
            info = cat_info.get(budget.category_id, {"name": f"ID:{budget.category_id}", "icon": ""})
            category_map[budget.category_id] = {"name": info["name"], "icon": info["icon"], "total_spent": 0.0, "budget": budget.target_amount}

        for t in transactions:
            if getattr(t, 'type', 'expense') != 'expense':
                continue
            if t.category_id not in category_map:
                info = cat_info.get(t.category_id, {"name": f"ID:{t.category_id}", "icon": ""})
                category_map[t.category_id] = {"name": info["name"], "icon": info["icon"], "total_spent": 0.0, "budget": 0.0}
            category_map[t.category_id]["total_spent"] += t.amount

        report["summary"] = {
            "total_spent": round(total_expense, 2),
            "total_budgeted": round(sum(b.target_amount for b in self.budget_repo.get_active_budgets_for_user(user_id=user_id, month=month, year=year)), 2),
            "total_income": round(total_income, 2),
            "opening_balance": round(opening_balance, 2),
            "closing_balance": round(closing_balance, 2),
        }
        report["detailed_spending"] = {
            cat_id: {"name": category_map[cat_id]["name"], "icon": category_map[cat_id]["icon"], "spent": round(category_map[cat_id]["total_spent"], 2), "budget": round(category_map[cat_id]["budget"], 2)}
            for cat_id in category_map
        }

        return report

    def update_transaction(self, tx_id: int, user_id: int, data: dict) -> Optional[Transaction]:
        allowed = {"amount", "category_id", "description", "date"}
        update = {k: v for k, v in data.items() if k in allowed}
        if not update:
            raise ValueError("Нет полей для обновления")
        if "amount" in update:
            update["amount"] = abs(float(update["amount"]))
        if "date" in update and isinstance(update["date"], str):
            from datetime import datetime
            update["date"] = datetime.strptime(update["date"], "%Y-%m-%d")
        if "category_id" in update:
            from models.database import Category
            from utils.database_session import get_db
            with get_db() as s:
                cat = s.query(Category).filter(Category.id == update["category_id"]).first()
                update["type"] = cat.type if cat else "expense"
        tx = self.transaction_repo.update_transaction(tx_id, user_id, update)
        if not tx:
            raise ValueError("Транзакция не найдена")
        return tx

    def delete_transaction(self, tx_id: int, user_id: int) -> bool:
        return self.transaction_repo.delete_transaction(tx_id, user_id)

    def get_user_transactions(self, user_id: int) -> list:
        from models.database import Category
        from utils.database_session import get_db

        transactions = self.transaction_repo.get_all_for_user(user_id)
        with get_db() as session:
            cats = {c.id: {"name": c.name, "icon": c.icon or ""} for c in session.query(Category).all()}
        result = []
        for t in transactions:
            cat = cats.get(t.category_id, {"name": f"ID:{t.category_id}", "icon": "📁"})
            result.append({
                "id": t.id,
                "amount": t.amount,
                "category_id": t.category_id,
                "category_name": cat["name"],
                "category_icon": cat["icon"],
                "description": t.description or "",
                "date": t.date.isoformat() if t.date else "",
                "type": getattr(t, 'type', 'expense'),
            })
        return result

    def get_filtered_user_transactions(self, user_id: int, month: int = None, year: int = None, category_id: int = None, page: int = 1, limit: int = 50) -> dict:
        from models.database import Category
        from utils.database_session import get_db

        transactions, total = self.transaction_repo.get_filtered_for_user(
            user_id, month=month, year=year, category_id=category_id, page=page, limit=limit
        )
        with get_db() as session:
            cats = {c.id: {"name": c.name, "icon": c.icon or ""} for c in session.query(Category).all()}
        result = []
        for t in transactions:
            cat = cats.get(t.category_id, {"name": f"ID:{t.category_id}", "icon": "📁"})
            result.append({
                "id": t.id,
                "amount": t.amount,
                "category_id": t.category_id,
                "category_name": cat["name"],
                "category_icon": cat["icon"],
                "description": t.description or "",
                "date": t.date.isoformat() if t.date else "",
                "type": getattr(t, 'type', 'expense'),
            })
        return {"data": result, "total": total, "page": page, "limit": limit,
                "month": month, "year": year}

    def process_regular_payments(self, user_id: int) -> dict:
        if not self.income_repo:
            return {"processed": 0, "errors": ["income_repo не подключён"]}
        from datetime import datetime
        due = self.income_repo.get_due_regular(user_id)
        processed = 0
        errors = []
        for src in due:
            try:
                from datetime import datetime
                txn_date = src.next_date or datetime.combine(date.today(), datetime.min.time())
                self.add_transaction(
                    user_id=user_id,
                    amount=abs(src.amount),
                    category_id=src.category_id,
                    description=f"[Авто] {src.name}: {src.description or src.name}",
                    date=txn_date,
                )
                # Рассчитываем следующую дату
                next_d = txn_date
                if src.period == "daily":
                    from datetime import timedelta as tdelta
                    next_d = next_d + tdelta(days=1)
                elif src.period == "weekly":
                    next_d = next_d + tdelta(weeks=1)
                elif src.period == "monthly":
                    m = next_d.month + 1
                    y = next_d.year
                    if m > 12:
                        m = 1; y += 1
                    max_day = monthrange(y, m)[1]
                    day = min(src.day_of_period, max_day)
                    next_d = date(y, m, day)
                elif src.period == "yearly":
                    y = next_d.year + 1
                    max_day = monthrange(y, next_d.month)[1]
                    day = min(src.day_of_period, max_day)
                    next_d = date(y, next_d.month, day)
                else:
                    next_d = next_d + tdelta(days=30)
                self.income_repo.update(src.id, user_id, {"next_date": next_d})
                processed += 1
            except Exception as e:
                errors.append(f"{src.name}: {str(e)}")
        return {"processed": processed, "errors": errors}