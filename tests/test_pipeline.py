"""Tests (run from the project root: python -m unittest discover tests)."""

import unittest
from collections import Counter
from itertools import islice
from pathlib import Path

from bank_stream.analytics import calculate_statistics, running_totals
from bank_stream.batches import batched
from bank_stream.filters import find_account
from bank_stream.pipeline import build_pipeline
from bank_stream.readers import RecordFile
from bank_stream.utils import account_numbers, flatten, take

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample.csv"


class PipelineTest(unittest.TestCase):
    def test_validation_counts_invalid_records(self) -> None:
        stats: Counter[str] = Counter()
        records = list(build_pipeline(SAMPLE, stats=stats))
        self.assertEqual(stats["rows"], 10)
        self.assertEqual(len(records), 5)
        self.assertEqual(sum(v for k, v in stats.items() if k.startswith("invalid")), 5)

    def test_negative_balance_is_not_allowed(self) -> None:
        records = {r.account_number: r for r in build_pipeline(SAMPLE)}
        rejected = records["UA10000003"]
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.balance_after, 2150.75)
        self.assertEqual(records["UA10000010"].balance_after, 0.0)
        self.assertTrue(all(r.balance_after >= 0 for r in records.values()))

    def test_transformation_and_statistics(self) -> None:
        records = list(build_pipeline(SAMPLE))
        self.assertEqual(records[2].client, "Андрій Мельник")
        stats = calculate_statistics(iter(records))
        self.assertEqual(stats["total_funds"], 12_500 + 500 + 40_000 + 2_150.75 + 100_000)
        self.assertEqual(list(running_totals(records))[-1], stats["total_funds"])

    def test_lazy_search_and_filters(self) -> None:
        self.assertEqual(find_account(build_pipeline(SAMPLE), "ua10000004").balance_after,
                         100_000.0)
        self.assertIsNone(find_account(build_pipeline(SAMPLE), "UA99999999"))
        rich = list(build_pipeline(SAMPLE, client="о", min_balance=20_000))
        self.assertEqual([r.account_number for r in rich], ["UA10000002", "UA10000004"])

    def test_generator_is_one_shot_but_record_file_is_not(self) -> None:
        pipeline = build_pipeline(SAMPLE)
        self.assertEqual(len(list(pipeline)), 5)
        self.assertEqual(list(pipeline), [])
        sample = RecordFile(SAMPLE)
        self.assertEqual(len(list(sample)), len(list(sample)))

    def test_helpers(self) -> None:
        self.assertEqual([len(b) for b in batched(range(7), 3)], [3, 3, 1])
        self.assertEqual(take(2, account_numbers(5)), ["UA00000005", "UA00000006"])
        self.assertEqual(list(flatten([1, [2, [3]], []])), [1, 2, 3])
        self.assertEqual(list(islice(account_numbers(), 0)), [])


if __name__ == "__main__":
    unittest.main()
