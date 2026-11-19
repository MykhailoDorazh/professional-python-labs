"""CSV -> validation -> departments -> statistics -> JSON + report on real temporary files."""

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from employee_app.app import run_flow
from employee_app.config import AppConfig, load_config
from employee_app.exceptions import RecordValidationError

pytestmark = pytest.mark.integration


def test_full_flow_tolerant(project_dir: Path, notifier: Mock) -> None:
    config = load_config(project_dir / "config.yaml")
    result = run_flow(project_dir / "data/employees.csv", project_dir / "output", config,
                      notifier)

    assert (result.employees, result.invalid, result.rejected, result.exported) == (4, 3, 1, 4)
    assert result.payroll == pytest.approx(251_800)
    assert result.average == pytest.approx(62_950)
    assert result.highest == "E0001"
    data = json.loads((project_dir / "output/employees.json").read_text(encoding="utf-8"))
    assert {item["employee_id"]: item["department"] for item in data} == {
        "E0001": "IT", "E0002": "IT", "E0003": "FIN", "E0004": "HR"}
    report = (project_dir / "output/payroll_2026-11.txt").read_text(encoding="utf-8")
    assert "IT: 2 осіб, фонд 167000.00" in report
    assert notifier.send.call_count == 4  # 4 зарахування


def test_strict_flow_creates_no_output(project_dir: Path, notifier: Mock,
                                       config: AppConfig) -> None:
    with pytest.raises(RecordValidationError):
        run_flow(project_dir / "data/employees.csv", project_dir / "output",
                 replace(config, skip_invalid=False), notifier)
    assert not (project_dir / "output").exists()


def test_flow_with_min_salary_from_environment(project_dir: Path, notifier: Mock,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMPLOYEE_MIN_SALARY", "40000")
    config = load_config(project_dir / "config.yaml")
    result = run_flow(project_dir / "data/employees.csv", project_dir / "out", config, notifier)
    assert result.employees == 3  # E0003 (36 800) тепер нижче мінімуму
    assert result.invalid == 4
