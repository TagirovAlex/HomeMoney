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

    def test_add_transaction_amount_too_high(self, service):
        with pytest.raises(ValueError, match="Недопустимый диапазон"):
            service.add_transaction(1, 200000, 2)

    def test_add_transaction_negative_amount(self, service):
        with pytest.raises(ValueError, match="Недопустимый диапазон"):
            service.add_transaction(1, -50, 2)

    def test_get_monthly_summary(self, service, mock_tx_repo, mock_budget_repo):
        mock_tx = MagicMock()
        mock_tx.amount = 300.0
        mock_tx_repo.get_transactions_by_user.return_value = [mock_tx, mock_tx]
        mock_budget_repo.get_active_budgets_for_user.return_value = []
        summary = service.get_monthly_summary(1, 5, 2024)
        assert summary["total_spent"] == 600.0
        assert summary["total_budgeted"] == 0.0
        assert summary["transactions_count"] == 2

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

    def test_create_budget(self, service, mock_budget_repo):
        mock_budget_repo.create_budget.return_value = MagicMock(id=1)
        budget = service.create_budget(category_id=1, target_amount=1000.0, user_id=1)
        assert budget.id == 1
        mock_budget_repo.create_budget.assert_called_once_with({"user_id": 1, "category_id": 1, "target_amount": 1000.0})

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
