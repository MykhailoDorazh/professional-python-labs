"""Bank analytics on a large in-memory dataset: baseline Python vs NumPy.

All money values are integer cents, so Python and NumPy results can be
compared exactly (``==``) instead of with a floating point tolerance.

Workloads:
* ``replay_balances`` / ``transaction_stats`` — aggregation of a long history
  of operations (total funds, turnover, statistics of amounts);
* ``project_balance`` — CPU-heavy daily interest accrual for one year with
  rounding to cents every day (bank rule), done for every account.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import numpy.typing as npt

DEPOSIT, WITHDRAW = 0, 1
RATE_BP = {"current": 50, "savings": 1200}  # annual rate, basis points (0.5 %, 12 %)
DAYS = 365
DAY_DENOMINATOR = DAYS * 10_000

IntArray = npt.NDArray[np.int64]


@dataclass(frozen=True)
class Dataset:
    """Column-oriented data: accounts and a long history of operations."""

    initial: list[int]  # opening balance of every account, cents
    rate_bp: list[int]  # interest rate of every account, basis points
    op_account: list[int]  # account index of every operation
    op_kind: list[int]  # DEPOSIT / WITHDRAW
    op_amount: list[int]  # cents, > 0

    @property
    def n_accounts(self) -> int:
        return len(self.initial)

    @property
    def n_operations(self) -> int:
        return len(self.op_amount)

    def as_numpy(self) -> NumpyDataset:
        return NumpyDataset(
            np.asarray(self.initial, dtype=np.int64),
            np.asarray(self.rate_bp, dtype=np.int64),
            np.asarray(self.op_account, dtype=np.int64),
            np.asarray(self.op_kind, dtype=np.int64),
            np.asarray(self.op_amount, dtype=np.int64),
        )


@dataclass(frozen=True)
class NumpyDataset:
    initial: IntArray
    rate_bp: IntArray
    op_account: IntArray
    op_kind: IntArray
    op_amount: IntArray


def generate_dataset(n_accounts: int, n_operations: int, seed: int = 42) -> Dataset:
    """Deterministic synthetic bank: deposits are 3x more frequent than withdrawals.

    Withdrawals never exceed what was deposited earlier on the account, so
    the replayed balance is never negative (as in the real system).
    """
    rng = random.Random(seed)
    initial = [rng.randrange(0, 5_000_000) for _ in range(n_accounts)]  # 0..50 000 UAH
    rate_bp = [RATE_BP["savings"] if rng.random() < 0.3 else RATE_BP["current"]
               for _ in range(n_accounts)]
    balance = initial.copy()
    op_account, op_kind, op_amount = [], [], []
    for _ in range(n_operations):
        acc = rng.randrange(n_accounts)
        amount = rng.randrange(100, 2_000_000)  # 1..20 000 UAH
        if rng.random() < 0.25 and balance[acc] >= amount:
            kind = WITHDRAW
            balance[acc] -= amount
        else:
            kind = DEPOSIT
            balance[acc] += amount
        op_account.append(acc)
        op_kind.append(kind)
        op_amount.append(amount)
    return Dataset(initial, rate_bp, op_account, op_kind, op_amount)


# ---------- workload 1: aggregation of history ----------
def replay_balances_python(data: Dataset) -> list[int]:
    """Baseline: final balance of every account = opening + history."""
    balances = data.initial.copy()
    for acc, kind, amount in zip(data.op_account, data.op_kind, data.op_amount, strict=True):
        if kind == DEPOSIT:
            balances[acc] += amount
        else:
            balances[acc] -= amount
    return balances


def replay_balances_numpy(data: NumpyDataset) -> IntArray:
    """Vectorized: signed amounts summed per account with np.bincount."""
    signed = np.where(data.op_kind == DEPOSIT, data.op_amount, -data.op_amount)
    delta = np.bincount(data.op_account, weights=signed, minlength=len(data.initial))
    return data.initial + delta.astype(np.int64)


def transaction_stats_python(data: Dataset) -> dict[str, float]:
    """Count / turnover / mean / std / min / max of operation amounts."""
    amounts = data.op_amount
    count = len(amounts)
    total = 0
    minimum = maximum = amounts[0]
    for value in amounts:
        total += value
        if value < minimum:
            minimum = value
        if value > maximum:
            maximum = value
    mean = total / count
    variance = 0.0
    for value in amounts:
        variance += (value - mean) ** 2
    deposits = sum(1 for kind in data.op_kind if kind == DEPOSIT)
    return {"count": count, "turnover": total, "mean": mean,
            "std": math.sqrt(variance / count), "min": minimum, "max": maximum,
            "deposits": deposits, "withdrawals": count - deposits}


def transaction_stats_numpy(data: NumpyDataset) -> dict[str, float]:
    a = data.op_amount
    deposits = int(np.count_nonzero(data.op_kind == DEPOSIT))
    return {"count": int(a.size), "turnover": int(a.sum()), "mean": float(a.mean()),
            "std": float(a.std()), "min": int(a.min()), "max": int(a.max()),
            "deposits": deposits, "withdrawals": int(a.size) - deposits}


def total_funds_python(balances: list[int]) -> int:
    total = 0
    for value in balances:
        total += value
    return total


# ---------- workload 2: CPU-bound interest projection ----------
def daily_interest(balance: int, rate_bp: int) -> int:
    """Interest for one day, rounded half up to a cent (exact integer arithmetic)."""
    return (2 * balance * rate_bp + DAY_DENOMINATOR) // (2 * DAY_DENOMINATOR)


def project_balance(balance: int, rate_bp: int, days: int = DAYS) -> int:
    """Balance after `days` of daily accrual — 365 dependent steps per account."""
    for _ in range(days):
        balance += (2 * balance * rate_bp + DAY_DENOMINATOR) // (2 * DAY_DENOMINATOR)
    return balance


def project_chunk(chunk: tuple[list[int], list[int]]) -> list[int]:
    """Projection of a chunk of accounts (unit of work for thread/process pools)."""
    balances, rates = chunk
    return [project_balance(b, r) for b, r in zip(balances, rates, strict=True)]


def project_balances_python(balances: list[int], rates: list[int]) -> list[int]:
    """Baseline: one account after another."""
    return project_chunk((balances, rates))


def project_balances_numpy(balances: IntArray, rates: IntArray, days: int = DAYS) -> IntArray:
    """Vectorized over accounts: 365 array operations instead of 365 * N Python steps."""
    result = balances.astype(np.int64).copy()
    rates = rates.astype(np.int64)
    for _ in range(days):
        result += (2 * result * rates + DAY_DENOMINATOR) // (2 * DAY_DENOMINATOR)
    return result


# ---------- report used for profiling ----------
def build_report(data: Dataset) -> dict[str, object]:
    """Baseline daily report: everything in pure Python (profiled with cProfile)."""
    balances = replay_balances_python(data)
    stats = transaction_stats_python(data)
    projected = project_balances_python(balances, data.rate_bp)
    top = sorted(range(len(balances)), key=balances.__getitem__, reverse=True)[:10]
    return {"total_funds": total_funds_python(balances), "stats": stats,
            "projected_total": total_funds_python(projected), "top_accounts": top}


def build_report_optimized(data: Dataset, arrays: NumpyDataset | None = None) -> dict[str, object]:
    """The same report with the fastest variants chosen by the benchmark (NumPy)."""
    arrays = arrays or data.as_numpy()
    balances = replay_balances_numpy(arrays)
    projected = project_balances_numpy(balances, arrays.rate_bp)
    top = np.argsort(-balances, kind="stable")[:10]
    return {"total_funds": int(balances.sum()), "stats": transaction_stats_numpy(arrays),
            "projected_total": int(projected.sum()), "top_accounts": [int(i) for i in top]}


# ---------- caching ----------
class AccountStatistics:
    """Expensive per-account statistics with lru_cache and version-based invalidation.

    The cache key is (account, version). Every new operation of an account
    increments its version, so the next request is a cache miss and the stale
    entry is never returned.
    """

    def __init__(self, data: Dataset, maxsize: int = 1024) -> None:
        self.data = data
        self.versions: dict[int, int] = {}
        self._cached = lru_cache(maxsize=maxsize)(self._compute)

    def _compute(self, account: int, version: int) -> tuple[int, int, float]:
        """Scan of the whole history: (operations, balance, average amount)."""
        count = total = 0
        balance = self.data.initial[account]
        for acc, kind, amount in zip(self.data.op_account, self.data.op_kind,
                                     self.data.op_amount, strict=True):
            if acc == account:
                count += 1
                total += amount
                balance += amount if kind == DEPOSIT else -amount
        return count, balance, total / count if count else 0.0

    def get(self, account: int) -> tuple[int, int, float]:
        return self._cached(account, self.versions.get(account, 0))

    def add_operation(self, account: int, kind: int, amount: int) -> None:
        self.data.op_account.append(account)
        self.data.op_kind.append(kind)
        self.data.op_amount.append(amount)
        self.versions[account] = self.versions.get(account, 0) + 1  # invalidation

    def cache_info(self) -> object:
        return self._cached.cache_info()

    def clear(self) -> None:
        self._cached.cache_clear()
