"""Tests (run: python -m unittest discover tests)."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from bank_io.app import run_pipeline
from bank_io.config import load_config
from bank_io.exceptions import ConfigurationError, InsufficientFundsError, RecordValidationError
from bank_io.utils import mask_account, mask_client
from bank_io.validators import parse_operation

ROOT = Path(__file__).resolve().parents[1]


class BankIoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        config = load_config(ROOT / "config.yaml", env={})
        self.config = replace(config, output_path=self.tmp / "out.json",
                              errors_path=self.tmp / "errors.csv",
                              summary_path=self.tmp / "summary.json")

    def row(self, **changes: str) -> dict[str, str]:
        row = {"account_number": "UA10000001", "client": "Іван", "balance": "100",
               "operation": "withdraw", "amount": "40"}
        row.update(changes)
        return row

    def test_parse_valid_operation(self) -> None:
        op = parse_operation(self.row(), line_number=2, config=self.config.processing)
        self.assertEqual(op.balance_after, 60.0)

    def test_negative_balance_and_chaining(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            parse_operation(self.row(amount="100.01"), line_number=2,
                            config=self.config.processing)
        with self.assertRaises(RecordValidationError) as ctx:
            parse_operation(self.row(amount="x"), line_number=7, config=self.config.processing)
        self.assertIsInstance(ctx.exception.__cause__, ValueError)
        self.assertEqual((ctx.exception.line_number, ctx.exception.field), (7, "amount"))

    def test_tolerant_pipeline(self) -> None:
        stats = run_pipeline(self.config)
        self.assertEqual((stats.total, stats.valid, stats.invalid), (12, 4, 8))
        data = json.loads(self.config.output_path.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 4)

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
        config = load_config(ROOT / "config.yaml", env={"BANK_IO_SKIP_INVALID": "false"})
        self.assertFalse(config.processing.skip_invalid)

    def test_masking(self) -> None:
        self.assertEqual(mask_account("UA10000123"), "UA******23")
        self.assertEqual(mask_client("Іван Петренко"), "І*** П***")


if __name__ == "__main__":
    unittest.main()
