import pytest
from unittest.mock import MagicMock, create_autospec
from services.financial_service import FinancialService
from data_access.repositories.transaction_repository import ITransactionRepository
from data_access.repositories.budget_repository import IBudgetRepository

@pytest.fixture
def mock_tx_repo():
    return create_autospec(ITransactionRepository)

@pytest.fixture
def mock_budget_repo():
    return create_autospec(IBudgetRepository)

@pytest.fixture
def service(mock_tx_repo, mock_budget_repo):
    return FinancialService(
        transaction_repo=mock_tx_repo,
        budget_repo=mock_budget_repo
    )

class TestFinancialService:
    def test_add_transaction_valid(self, service, mock_tx_repo):
        mock_tx_repo.add_transaction.return_value = MagicMock(id=1)
        tx = service.add_transaction(1, 500.0, 2, "test")
        assert tx.id == 1
        mock_tx_repo.add_transaction.assert_called_once()

    def test_add_transaction_large_amount(self, service, mock_tx_repo):
        mock_tx_repo.add_transaction.return_value = MagicMock(id=2)
        tx = service.add_transaction(1, 200000, 2)
        assert tx.id == 2
        mock_tx_repo.add_transaction.assert_called_once()

    def test_add_transaction_negative_amount(self, service):
        with pytest.raises(ValueError, match="положительным числом"):
            service.add_transaction(1, -50, 2)

    def test_get_monthly_summary(self, service, mock_tx_repo, mock_budget_repo):
        tx1 = MagicMock()
        tx1.amount = 500.0
        tx1.type = "expense"
        tx2 = MagicMock()
        tx2.amount = 300.0
        tx2.type = "income"
        tx3 = MagicMock()
        tx3.amount = 100.0
        tx3.type = "expense"
        mock_tx_repo.get_transactions_by_user.return_value = [tx1, tx2, tx3]
        mock_budget_repo.get_active_budgets_for_user.return_value = []
        summary = service.get_monthly_summary(1, 5, 2024)
        assert summary["total_spent"] == 600.0
        assert summary["total_income"] == 300.0
        assert summary["total_budgeted"] == 0.0
        assert summary["transactions_count"] == 3

    def test_check_budget_exceeded(self, service, mock_tx_repo, mock_budget_repo):
        mock_tx = MagicMock()
        mock_tx.amount = 500.0
        mock_tx.category_id = 1
        mock_tx_repo.get_transactions_by_user.return_value = [mock_tx, mock_tx]
        mock_budget = MagicMock()
        mock_budget.category_id = 1
        mock_budget.target_amount = 800.0
        mock_budget_repo.get_active_budgets_for_user.return_value = [mock_budget]
        assert service.check_budget_exceeded(1, 1, 5, 2024) is True

    def test_check_budget_not_exceeded(self, service, mock_tx_repo, mock_budget_repo):
        mock_tx = MagicMock()
        mock_tx.amount = 100.0
        mock_tx.category_id = 1
        mock_tx_repo.get_transactions_by_user.return_value = [mock_tx]
        mock_budget = MagicMock()
        mock_budget.category_id = 1
        mock_budget.target_amount = 500.0
        mock_budget_repo.get_active_budgets_for_user.return_value = [mock_budget]
        assert service.check_budget_exceeded(1, 1, 5, 2024) is False

    def test_create_template(self, service, mock_budget_repo):
        mock_budget_repo.get_template_for_category.return_value = None
        mock_budget_repo.create_budget.return_value = MagicMock(id=1)
        budget = service.create_budget(category_id=1, target_amount=1000.0, user_id=1)
        assert budget.id == 1
        mock_budget_repo.create_budget.assert_called_once_with({"user_id": 1, "category_id": 1, "target_amount": 1000.0})

    def test_update_template_upsert(self, service, mock_budget_repo):
        existing = MagicMock(id=5)
        mock_budget_repo.get_template_for_category.return_value = existing
        mock_budget_repo.update_budget.return_value = MagicMock(id=5, target_amount=2000.0)
        budget = service.create_budget(category_id=1, target_amount=2000.0, user_id=1)
        assert budget.id == 5
        mock_budget_repo.update_budget.assert_called_once_with(5, 1, {"target_amount": 2000.0})

    def test_create_override(self, service, mock_budget_repo):
        mock_budget_repo.get_override.return_value = None
        mock_budget_repo.create_budget.return_value = MagicMock(id=2)
        budget = service.create_budget(category_id=1, target_amount=1500.0, user_id=1, month=6, year=2026)
        assert budget.id == 2
        mock_budget_repo.create_budget.assert_called_once_with(
            {"user_id": 1, "category_id": 1, "target_amount": 1500.0, "month": 6, "year": 2026}
        )

    def test_update_override_upsert(self, service, mock_budget_repo):
        existing = MagicMock(id=3)
        mock_budget_repo.get_override.return_value = existing
        mock_budget_repo.update_budget.return_value = MagicMock(id=3, target_amount=2500.0)
        budget = service.create_budget(category_id=1, target_amount=2500.0, user_id=1, month=6, year=2026)
        assert budget.id == 3
        mock_budget_repo.update_budget.assert_called_once_with(3, 1, {"target_amount": 2500.0})

    def test_copy_overrides(self, service, mock_budget_repo):
        o1 = MagicMock(category_id=1, target_amount=5000.0)
        o2 = MagicMock(category_id=2, target_amount=3000.0)
        mock_budget_repo.get_overrides_for_month.return_value = [o1, o2]
        mock_budget_repo.get_override.return_value = None
        mock_budget_repo.create_budget.return_value = MagicMock(id=99)
        copied = service.copy_overrides(1, 5, 2026, 6, 2026)
        assert copied == 2
        assert mock_budget_repo.create_budget.call_count == 2

    def test_process_regular_payments_no_repo(self, service):
        result = service.process_regular_payments(1)
        assert result["processed"] == 0
        assert "income_repo не подключён" in str(result["errors"])

    def test_process_regular_payments_empty(self, service, mock_tx_repo, mock_budget_repo):
        from data_access.repositories.income_repository import IIncomeSourceRepository
        mock_income_repo = create_autospec(IIncomeSourceRepository)
        mock_income_repo.get_due_regular.return_value = []
        service.income_repo = mock_income_repo
        result = service.process_regular_payments(1)
        assert result["processed"] == 0
        assert result["errors"] == []
