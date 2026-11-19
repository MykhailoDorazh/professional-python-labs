import json
from pathlib import Path

import pytest

from bank_app import exporter
from bank_app.exceptions import DataExportError
from bank_app.exporter import AtomicWriter, export_accounts_json
from bank_app.models import Account


def test_export_accounts_json(tmp_path: Path, current_account: Account) -> None:
    output = tmp_path / "out" / "accounts.json"
    assert export_accounts_json([current_account], output) == 1
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == [{"number": "UA100001", "type": "current", "owner": "Іван Петренко",
                     "balance": 1000.0, "currency": "UAH", "transactions": 0}]


def test_failed_export_keeps_old_output(tmp_path: Path, current_account: Account,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "accounts.json"
    output.write_text("old valid data", encoding="utf-8")

    def broken_dump(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(exporter.json, "dump", broken_dump)  # failure injection
    with pytest.raises(DataExportError) as exc_info:
        export_accounts_json([current_account], output)
    assert isinstance(exc_info.value.__cause__, OSError)
    assert output.read_text(encoding="utf-8") == "old valid data"
    assert not output.with_suffix(".json.tmp").exists()


def test_atomic_writer_cleanup_on_exception(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    writer = AtomicWriter(target)
    with pytest.raises(RuntimeError):
        with writer as file:
            file.write("partial")
            assert writer.temporary.exists()
            raise RuntimeError("boom")
    assert not writer.temporary.exists() and not target.exists()


def test_atomic_writer_success(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    with AtomicWriter(target) as file:
        file.write("complete")
    assert target.read_text(encoding="utf-8") == "complete"
