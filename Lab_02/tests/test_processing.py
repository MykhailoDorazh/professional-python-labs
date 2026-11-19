"""Tests (run: python -m unittest discover tests)."""

import unittest

from bank_analytics.analytics import (
    balance_range,
    create_account,
    richest_account,
    sum_values,
    type_summary,
)
from bank_analytics.data import accounts
from bank_analytics.processors import (
    count_by_type,
    create_account_index,
    filter_by_min_balance,
    find_account_linear,
    find_by_number,
    get_unique_clients,
    group_by_type,
    make_min_balance_filter,
    sort_by_balance,
)


class ProcessingTest(unittest.TestCase):
    def test_list_and_dict_search_agree(self) -> None:
        index = create_account_index(accounts)
        for account in accounts:
            number = account["number"]
            self.assertIs(find_account_linear(accounts, number),
                          find_by_number(index, number))
        self.assertIsNone(find_by_number(index, "UA000000"))

    def test_grouping_and_counting(self) -> None:
        groups = group_by_type(accounts)
        counter = count_by_type(accounts)
        self.assertEqual({t: len(v) for t, v in groups.items()}, dict(counter))
        self.assertEqual(len(get_unique_clients(accounts)), 7)

    def test_filter_and_sort(self) -> None:
        rich = sort_by_balance(filter_by_min_balance(accounts, 20_000))
        self.assertEqual([a["number"] for a in rich],
                         ["UA100006", "UA100004", "UA100002", "UA100010"])

    def test_closure_remembers_minimum(self) -> None:
        is_rich = make_min_balance_filter(100_000)
        self.assertTrue(is_rich({"balance": 100_000}))
        self.assertFalse(is_rich({"balance": 99_999.99}))

    def test_aggregation(self) -> None:
        self.assertEqual(richest_account(accounts)["number"], "UA100006")
        self.assertEqual(balance_range(accounts), (0.0, 150_000.0))
        self.assertEqual(sum_values(1, 2.5, 3), 6.5)
        self.assertEqual(type_summary(accounts)["кредитний"], (2, 950.0, 475.0))

    def test_create_account_validation(self) -> None:
        with self.assertRaises(ValueError):
            create_account(number="UA1", client="X", balance=-1, type="поточний")
        with self.assertRaises(ValueError):
            create_account(number="UA1", client="X")


if __name__ == "__main__":
    unittest.main()
