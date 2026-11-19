from collections.abc import Callable
from pathlib import Path

import pytest

from bank_app.config import AppConfig
from bank_app.exceptions import DataImportError, RecordValidationError
from bank_app.importer import (
    ImportStatistics,
    import_accounts,
    parse_operation,
    read_operations,
)
from bank_app.models import SavingsAccount

ACCOUNTS = ("number,type,owner_id,owner_name,owner_email,balance\n"
            "UA100001,savings,1,Іван Петренко,ivan@example.com,50000\n"
            "UA100002,current,2,Олена Коваль,olena@example.com,12.5\n")


def test_import_accounts(write_file: Callable[[str, str], Path]) -> None:
    accounts = import_accounts(write_file("accounts.csv", ACCOUNTS))
    assert [a.number for a in accounts] == ["UA100001", "UA100002"]
    assert isinstance(accounts[0], SavingsAccount)
    assert accounts[1].balance.amount == pytest.approx(12.5)


@pytest.mark.parametrize(
    ("row", "field"),
    [
        pytest.param("UA100001,current,1,Іван,ivan@example.com,abc", "balance", id="bad-balance"),
        pytest.param("UA100001,deposit,1,Іван,ivan@example.com,10", "type", id="bad-type"),
        pytest.param("UA1,current,1,Іван,ivan@example.com,10", None, id="bad-number"),
        pytest.param("UA100001,current,x,Іван,ivan@example.com,10", None, id="bad-owner-id"),
    ],
)
def test_malformed_account_record(write_file: Callable[[str, str], Path],
                                  row: str, field: str | None) -> None:
    path = write_file("accounts.csv", ACCOUNTS.splitlines()[0] + "\n" + row + "\n")
    with pytest.raises(RecordValidationError) as exc_info:
        import_accounts(path)
    assert exc_info.value.line_number == 2
    assert exc_info.value.field == field


def test_malformed_amount_is_chained() -> None:
    config = AppConfig(("deposit",), "UAH", 100.0, True)
    with pytest.raises(RecordValidationError) as exc_info:
        parse_operation({"account_number": "UA100001", "operation": "deposit",
                         "amount": "1O0"}, 5, config)
    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("amount", "valid"),
    [("-0.01", False), ("0", False), ("0.01", True), ("50", True),
     ("100000", True), ("100000.01", False)],
)
def test_operation_amount_boundaries(config: AppConfig, amount: str, valid: bool) -> None:
    row = {"account_number": "ua100001", "operation": "Deposit", "amount": amount}
    if valid:
        record = parse_operation(row, 2, config)
        assert record.account_number == "UA100001" and record.operation == "deposit"
    else:
        with pytest.raises(RecordValidationError, match="range"):
            parse_operation(row, 2, config)


OPERATIONS = ("account_number,operation,amount\n"
              "UA100001,deposit,10\nUA100001,transfer,5\nUA100001,withdraw,x\n"
              "UA100001,withdraw,3\n")


def test_tolerant_mode_skips_invalid(write_file: Callable[[str, str], Path],
                                     config: AppConfig) -> None:
    stats = ImportStatistics()
    records = list(read_operations(write_file("ops.csv", OPERATIONS), config, stats))
    assert [r.line_number for r in records] == [2, 5]
    assert (stats.total, stats.valid, stats.invalid) == (4, 2, 2)
    assert stats.errors[0].startswith("line 3")


def test_strict_mode_stops_at_first_error(write_file: Callable[[str, str], Path],
                                          config: AppConfig) -> None:
    from dataclasses import replace

    stats = ImportStatistics()
    strict = replace(config, skip_invalid=False)
    with pytest.raises(RecordValidationError, match="transfer"):
        list(read_operations(write_file("ops.csv", OPERATIONS), strict, stats))
    assert (stats.valid, stats.invalid) == (1, 1)


def test_missing_input_file(tmp_path: Path) -> None:
    with pytest.raises(DataImportError) as exc_info:
        import_accounts(tmp_path / "absent.csv")
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)
