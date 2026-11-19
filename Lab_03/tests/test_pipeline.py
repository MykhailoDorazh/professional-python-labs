"""Tests (run from the project root: python -m unittest discover tests)."""

import tempfile
import unittest
from collections import Counter
from itertools import islice
from pathlib import Path

from employee_stream.analytics import (
    calculate_statistics,
    count_by_department,
    highest_paid,
    running_payroll,
    streaming_average,
    streaming_payroll,
)
from employee_stream.batches import batched, export_batches
from employee_stream.filters import find_employee
from employee_stream.pipeline import build_pipeline
from employee_stream.readers import RecordFile
from employee_stream.utils import employee_ids, flatten, take

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample.csv"


class PipelineTest(unittest.TestCase):
    def test_streaming_validation_counts_invalid_records(self) -> None:
        stats: Counter[str] = Counter()
        records = list(build_pipeline(SAMPLE, stats=stats))
        self.assertEqual(stats["rows"], 10)
        self.assertEqual(len(records), 5)
        self.assertEqual(stats["invalid:salary"], 2)
        self.assertEqual(sum(v for k, v in stats.items() if k.startswith("invalid")), 5)

    def test_normalisation(self) -> None:
        records = {e.employee_id: e for e in build_pipeline(SAMPLE)}
        self.assertEqual(records["E100003"].name, "Андрій Мельник")
        self.assertEqual(records["E100003"].department, "Фінанси")

    def test_statistics_payroll_average_max(self) -> None:
        stats = calculate_statistics(build_pipeline(SAMPLE))
        self.assertEqual(stats["payroll"], 52_000 + 78_500 + 31_200 + 29_800 + 0)
        self.assertEqual(stats["average"], 38_300.0)
        self.assertEqual(stats["highest"].employee_id, "E100002")
        self.assertEqual(stats["lowest"].salary, 0.0)  # boundary value is valid
        self.assertEqual(stats["departments"], {"IT": 2, "Фінанси": 2, "HR": 1})

    def test_department_and_salary_filters(self) -> None:
        it = list(build_pipeline(SAMPLE, department="it"))
        self.assertEqual([e.employee_id for e in it], ["E100001", "E100002"])
        level = list(build_pipeline(SAMPLE, min_salary=30_000, max_salary=60_000))
        self.assertEqual([e.employee_id for e in level], ["E100001", "E100003"])

    def test_streaming_helpers(self) -> None:
        self.assertEqual(streaming_payroll(build_pipeline(SAMPLE)), 191_500)
        self.assertEqual(streaming_average(e.salary for e in build_pipeline(SAMPLE)), 38_300)
        self.assertEqual(streaming_average([]), 0.0)
        self.assertEqual(highest_paid(build_pipeline(SAMPLE)).name, "Олена Коваль")
        self.assertIsNone(highest_paid(iter([])))
        self.assertEqual(count_by_department(build_pipeline(SAMPLE))["IT"], 2)
        self.assertEqual(list(running_payroll(build_pipeline(SAMPLE)))[-1], 191_500)

    def test_lazy_search(self) -> None:
        self.assertEqual(find_employee(build_pipeline(SAMPLE), "e100004").position,
                         "HR-менеджер")
        self.assertIsNone(find_employee(build_pipeline(SAMPLE), "E999999"))

    def test_batch_export(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            files = list(export_batches(build_pipeline(SAMPLE), Path(folder), 2))
            self.assertEqual([f.name for f in files],
                             ["employees_001.csv", "employees_002.csv", "employees_003.csv"])
            self.assertEqual(len(files[-1].read_text(encoding="utf-8").splitlines()), 2)

    def test_generator_is_one_shot_but_record_file_is_not(self) -> None:
        pipeline = build_pipeline(SAMPLE)
        self.assertEqual(len(list(pipeline)), 5)
        self.assertEqual(list(pipeline), [])
        sample = RecordFile(SAMPLE)
        self.assertEqual(len(list(sample)), len(list(sample)))

    def test_helpers(self) -> None:
        self.assertEqual([len(b) for b in batched(range(7), 3)], [3, 3, 1])
        self.assertEqual(take(2, employee_ids(5)), ["E000005", "E000006"])
        self.assertEqual(list(flatten([1, [2, [3]], []])), [1, 2, 3])
        self.assertEqual(list(islice(employee_ids(), 0)), [])


if __name__ == "__main__":
    unittest.main()
