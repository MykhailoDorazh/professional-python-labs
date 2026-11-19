"""CSV -> validation -> domain operations -> JSON on real temporary files."""

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from bank_app.app import run_flow
from bank_app.config import AppConfig, load_config
from bank_app.exceptions import RecordValidationError

pytestmark = pytest.mark.integration


def test_full_flow_tolerant(project_dir: Path, notifier: Mock) -> None:
    config = load_config(project_dir / "config.yaml")
    result = run_flow(project_dir / "data/accounts.csv", project_dir / "data/operations.csv",
                      project_dir / "output/accounts.json", config, notifier)

    assert (result.accounts, result.applied, result.rejected, result.invalid) == (3, 3, 2, 2)
    assert result.total_funds == pytest.approx(66_000)
    data = json.loads((project_dir / "output/accounts.json").read_text(encoding="utf-8"))
    balances = {item["number"]: item["balance"] for item in data}
    assert balances == {"UA100001": 49_000.0, "UA100002": 5_000.0, "UA100003": 12_000.0}
    assert notifier.send.call_count == 3 + 3  # 3 відкриття + 3 успішні операції


def test_strict_flow_creates_no_output(project_dir: Path, notifier: Mock,
                                       config: AppConfig) -> None:
    with pytest.raises(RecordValidationError):
        run_flow(project_dir / "data/accounts.csv", project_dir / "data/operations.csv",
                 project_dir / "output/accounts.json", replace(config, skip_invalid=False),
                 notifier)
    assert not (project_dir / "output/accounts.json").exists()


def test_flow_with_usd_from_environment(project_dir: Path, notifier: Mock,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_CURRENCY", "USD")
    config = load_config(project_dir / "config.yaml")
    result = run_flow(project_dir / "data/accounts.csv", project_dir / "data/operations.csv",
                      project_dir / "out.json", config, notifier)
    data = json.loads((project_dir / "out.json").read_text(encoding="utf-8"))
    assert {item["currency"] for item in data} == {"USD"}
    assert result.applied == 3
