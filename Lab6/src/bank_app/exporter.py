"""Atomic JSON export."""

import json
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import TextIO

from bank_app.exceptions import DataExportError
from bank_app.models import Account


class AtomicWriter:
    """Writes into <name>.tmp and replaces the target only on success."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.temporary = path.with_suffix(path.suffix + ".tmp")
        self._file: TextIO | None = None

    def __enter__(self) -> TextIO:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.temporary.open("w", encoding="utf-8")
        return self._file

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 traceback: TracebackType | None) -> bool:
        assert self._file is not None
        self._file.close()
        if exc_type is not None:
            self.temporary.unlink(missing_ok=True)
            return False
        self.temporary.replace(self.path)
        return False


def account_to_dict(account: Account) -> dict[str, object]:
    return {"number": account.number, "type": account.account_type,
            "owner": account.owner.name, "balance": account.balance.amount,
            "currency": account.balance.currency, "transactions": len(account)}


def export_accounts_json(accounts: Iterable[Account], path: Path) -> int:
    try:
        with AtomicWriter(path) as file:
            data = [account_to_dict(account) for account in accounts]
            json.dump(data, file, ensure_ascii=False, indent=2)
    except (OSError, TypeError) as error:
        raise DataExportError(f"Cannot export accounts to {path}") from error
    return len(data)
