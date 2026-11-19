"""Correctness of optimized implementations: they must equal the baseline."""

from pathlib import Path

import numpy as np
import pytest

from bank_perf.analytics import (
    DEPOSIT,
    AccountStatistics,
    build_report,
    build_report_optimized,
    daily_interest,
    generate_dataset,
    project_balance,
    project_balances_numpy,
    project_balances_python,
    replay_balances_numpy,
    replay_balances_python,
    transaction_stats_numpy,
    transaction_stats_python,
)
from bank_perf.parallel import (
    SharedAccount,
    hammer,
    load_journals_sequential,
    load_journals_threads,
    project_balances_processes,
    project_balances_threading,
    project_balances_threads,
    split,
    write_journals,
)


@pytest.fixture(scope="module")
def data():  # type: ignore[no-untyped-def]
    return generate_dataset(2_000, 10_000, seed=7)


def test_dataset_is_deterministic() -> None:
    assert generate_dataset(50, 200, seed=1) == generate_dataset(50, 200, seed=1)
    assert generate_dataset(50, 200, seed=1) != generate_dataset(50, 200, seed=2)


def test_replayed_balances_are_never_negative(data) -> None:  # type: ignore[no-untyped-def]
    assert min(replay_balances_python(data)) >= 0


def test_replay_numpy_equals_python(data) -> None:  # type: ignore[no-untyped-def]
    assert replay_balances_numpy(data.as_numpy()).tolist() == replay_balances_python(data)


def test_stats_numpy_equals_python(data) -> None:  # type: ignore[no-untyped-def]
    py, vec = transaction_stats_python(data), transaction_stats_numpy(data.as_numpy())
    assert py.keys() == vec.keys()
    for key in py:
        assert vec[key] == pytest.approx(py[key], rel=1e-9)  # float tolerance, not ==


@pytest.mark.parametrize("balance, rate, expected", [
    (0, 1200, 0),
    (100_000, 0, 0),
    (365_000_000, 100, 10_000),        # exactly 100.00 UAH a day
    (1, 1200, 0),                      # 0.0003 cent is rounded down
    (15_208, 1200, 5),                 # 4.99999 -> 5 (half up)
])
def test_daily_interest_rounding(balance: int, rate: int, expected: int) -> None:
    assert daily_interest(balance, rate) == expected


def test_project_balance_compound_interest() -> None:
    # 1000.00 UAH at 12 % with daily capitalisation: ~ 1000 * e^0.12 = 1127.47
    assert project_balance(100_000, 1200) == pytest.approx(112_747, abs=2)
    assert project_balance(100_000, 1200, days=0) == 100_000


def test_projection_numpy_equals_python(data) -> None:  # type: ignore[no-untyped-def]
    balances = replay_balances_python(data)
    expected = project_balances_python(balances, data.rate_bp)
    result = project_balances_numpy(np.asarray(balances), np.asarray(data.rate_bp))
    assert result.tolist() == expected  # integer cents: exact equality


@pytest.mark.parametrize("parts", [1, 3, 4, 7])
def test_split_keeps_order_and_items(parts: int) -> None:
    balances, rates = list(range(10)), list(range(100, 110))
    chunks = split(balances, rates, parts)
    assert [b for chunk, _ in chunks for b in chunk] == balances
    assert [r for _, chunk in chunks for r in chunk] == rates


@pytest.mark.parametrize("implementation", [project_balances_threads,
                                            project_balances_threading,
                                            project_balances_processes])
def test_parallel_projection_equals_sequential(data, implementation) -> None:  # type: ignore[no-untyped-def]
    balances = replay_balances_python(data)[:500]
    rates = data.rate_bp[:500]
    assert implementation(balances, rates, 2) == project_balances_python(balances, rates)


def test_optimized_report_equals_baseline(data) -> None:  # type: ignore[no-untyped-def]
    baseline, optimized = build_report(data), build_report_optimized(data)
    assert optimized["total_funds"] == baseline["total_funds"]
    assert optimized["projected_total"] == baseline["projected_total"]
    assert optimized["top_accounts"] == baseline["top_accounts"]


def test_journals_threads_equal_sequential(tmp_path: Path, data) -> None:  # type: ignore[no-untyped-def]
    paths = write_journals(tmp_path, zip(data.op_account, data.op_kind, data.op_amount), 4)
    counts = load_journals_threads(paths, workers=4)
    assert counts == load_journals_sequential(paths)
    assert sum(counts) == data.n_operations


def test_cache_hit_miss_and_invalidation() -> None:
    data = generate_dataset(10, 300, seed=3)
    stats = AccountStatistics(data)
    first = stats.get(5)
    assert stats.get(5) == first
    info = stats.cache_info()
    assert (info.hits, info.misses) == (1, 1)  # type: ignore[attr-defined]
    stats.add_operation(5, DEPOSIT, 1_000)
    updated = stats.get(5)
    assert updated[0] == first[0] + 1                 # one more operation
    assert updated[1] == first[1] + 1_000             # new balance, not the stale one
    assert stats.cache_info().misses == 2  # type: ignore[attr-defined]
    stats.clear()
    assert stats.cache_info().currsize == 0  # type: ignore[attr-defined]


def test_lock_keeps_balance_consistent() -> None:
    account = SharedAccount(1_000_000)
    hammer(account, SharedAccount.deposit_safe, threads=8, rounds=500)
    assert account.balance == 1_000_000
    assert account.operations == 8 * 500
