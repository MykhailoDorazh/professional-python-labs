"""Integration flow: import accounts -> apply operations -> export."""

import logging
from dataclasses import dataclass
from pathlib import Path

from bank_app.config import AppConfig
from bank_app.exceptions import AccountNotFoundError, InsufficientFundsError
from bank_app.exporter import export_accounts_json
from bank_app.importer import ImportStatistics, import_accounts, read_operations
from bank_app.models import Account
from bank_app.protocols import Notifier
from bank_app.repositories import InMemoryRepository
from bank_app.services import BankService, ReportService

logger = logging.getLogger(__name__)


@dataclass
class FlowResult:
    accounts: int
    applied: int
    rejected: int
    invalid: int
    exported: int
    total_funds: float


def run_flow(accounts_csv: Path, operations_csv: Path, output: Path,
             config: AppConfig, notifier: Notifier) -> FlowResult:
    repository: InMemoryRepository[Account] = InMemoryRepository()
    bank = BankService(repository, notifier)
    for account in import_accounts(accounts_csv, config.currency):
        bank.open_account(account)

    statistics = ImportStatistics()
    applied = rejected = 0
    for record in read_operations(operations_csv, config, statistics):
        try:
            if record.operation == "deposit":
                bank.deposit(record.account_number, record.amount)
            else:
                bank.withdraw(record.account_number, record.amount)
            applied += 1
        except (InsufficientFundsError, AccountNotFoundError) as error:
            rejected += 1
            logger.warning("Line %s rejected: %s", record.line_number, error)

    exported = export_accounts_json(repository, output)
    total = ReportService(repository).total_funds(config.currency).amount
    return FlowResult(len(repository), applied, rejected, statistics.invalid, exported, total)
