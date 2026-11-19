"""Tests (run: python -m unittest discover tests)."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from employee_io.app import run_pipeline
from employee_io.config import load_config
from employee_io.exceptions import (
    ConfigurationError,
    RecordValidationError,
    SalaryValidationError,
)
from employee_io.utils import mask_id, mask_name, salary_band
from employee_io.validators import parse_employee

ROOT = Path(__file__).resolve().parents[1]


class EmployeeIoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        config = load_config(ROOT / "config.yaml", env={})
        self.config = replace(config, output_path=self.tmp / "out.json",
                              errors_path=self.tmp / "errors.csv",
                              summary_path=self.tmp / "summary.json")

    def row(self, **changes: str) -> dict[str, str]:
        row = {"employee_id": "E100001", "name": " Іван   Петренко ", "position": "Розробник",
               "department": "it", "salary": "52000"}
        row.update(changes)
        return row

    def test_parse_valid_employee(self) -> None:
        employee = parse_employee(self.row(), line_number=2, config=self.config.processing)
        self.assertEqual((employee.name, employee.department, employee.salary),
                         ("Іван Петренко", "IT", 52_000.0))
        zero = parse_employee(self.row(salary="0"), line_number=2, config=self.config.processing)
        self.assertEqual(zero.salary, 0.0)  # boundary value is valid

    def test_invalid_fields_and_chaining(self) -> None:
        for field, value in (("employee_id", "E12AB"), ("name", " "), ("position", ""),
                             ("department", "Маркетинг")):
            with self.assertRaises(RecordValidationError) as ctx:
                parse_employee(self.row(**{field: value}), line_number=3,
                               config=self.config.processing)
            self.assertEqual(ctx.exception.field, field)
        with self.assertRaises(SalaryValidationError):
            parse_employee(self.row(salary="-0.01"), line_number=2, config=self.config.processing)
        with self.assertRaises(SalaryValidationError) as ctx:
            parse_employee(self.row(salary="x"), line_number=7, config=self.config.processing)
        self.assertIsInstance(ctx.exception.__cause__, ValueError)
        self.assertEqual((ctx.exception.line_number, ctx.exception.field), (7, "salary"))
        self.assertEqual(str(ctx.exception), "Salary must be numeric")  # value is not disclosed

    def test_tolerant_pipeline_with_salary_filter(self) -> None:
        stats = run_pipeline(self.config)
        self.assertEqual((stats.total, stats.valid, stats.invalid, stats.filtered),
                         (12, 5, 7, 1))
        data = json.loads(self.config.output_path.read_text(encoding="utf-8"))
        self.assertEqual([e["employee_id"] for e in data],
                         ["E100001", "E100002", "E100003", "E100012"])
        self.assertEqual(data[-1]["department"], "Продажі")
        self.assertEqual(stats.payroll, 207_701.25)
        summary = json.loads(self.config.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["invalid_by_field"]["salary"], 3)

    def test_strict_pipeline_keeps_old_output(self) -> None:
        self.config.output_path.write_text("old", encoding="utf-8")
        strict = replace(self.config, processing=replace(self.config.processing,
                                                         skip_invalid=False))
        with self.assertRaises(RecordValidationError):
            run_pipeline(strict)
        self.assertEqual(self.config.output_path.read_text(encoding="utf-8"), "old")
        self.assertFalse(self.config.output_path.with_suffix(".json.tmp").exists())

    def test_config_errors_and_env_override(self) -> None:
        with self.assertRaises(ConfigurationError):
            load_config(self.tmp / "missing.yaml")
        config = load_config(ROOT / "config.yaml", env={"EMPLOYEE_IO_SKIP_INVALID": "false",
                                                        "EMPLOYEE_IO_MIN_SALARY": "50000"})
        self.assertFalse(config.processing.skip_invalid)
        self.assertEqual(config.processing.min_salary, 50_000)
        self.assertIn("Логістика", config.processing.allowed_departments)
        with self.assertRaises(ConfigurationError):
            load_config(ROOT / "config.yaml", env={"EMPLOYEE_IO_MIN_SALARY": "-1"})

    def test_masking(self) -> None:
        self.assertEqual(mask_id("E100123"), "E1****3")
        self.assertEqual(mask_name("Іван Петренко"), "І*** П***")
        self.assertEqual(salary_band(52_000), "50000-59999")


if __name__ == "__main__":
    unittest.main()
