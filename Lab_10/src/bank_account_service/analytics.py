"""Interest forecast kept from laboratory work 9 (NumPy won the benchmark).

All values are integer cents; daily accrual is rounded half up to a cent.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

RATE_BP = {"current": 50, "savings": 1200}  # annual rate in basis points: 0.5 % and 12 %
DAYS = 365
DAY_DENOMINATOR = DAYS * 10_000

IntArray = npt.NDArray[np.int64]


def project_balance(balance: int, rate_bp: int, days: int = DAYS) -> int:
    """Reference implementation for one account (pure Python, used in tests)."""
    for _ in range(days):
        balance += (2 * balance * rate_bp + DAY_DENOMINATOR) // (2 * DAY_DENOMINATOR)
    return balance


def project_balances(balances: IntArray, rates: IntArray, days: int = DAYS) -> IntArray:
    """Balances of all accounts after `days` of daily capitalisation, vectorized.

    Args:
        balances: current balances in cents.
        rates: annual interest rates in basis points.
        days: number of days to accrue.

    Returns:
        Projected balances in cents (same order as the input).
    """
    result = balances.astype(np.int64).copy()
    rates = rates.astype(np.int64)
    for _ in range(days):
        result += (2 * result * rates + DAY_DENOMINATOR) // (2 * DAY_DENOMINATOR)
    return result
