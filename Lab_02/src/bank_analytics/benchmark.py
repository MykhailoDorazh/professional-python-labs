"""Benchmark: search in list vs dict-index, membership in list vs set."""

import random
from time import perf_counter

from bank_analytics.data import ACCOUNT_TYPES
from bank_analytics.processors import create_account_index, find_account_linear

SIZES: tuple[int, ...] = (1_000, 10_000, 100_000)
LOOKUPS: int = 500


def generate_accounts(count: int, seed: int = 42) -> list[dict]:
    """Synthetic data set of `count` accounts (list comprehension)."""
    rng = random.Random(seed)
    return [
        {
            "number": f"UA{100_000 + i:07d}",
            "client": f"Клієнт {rng.randint(1, count // 2 + 1)}",
            "balance": round(rng.uniform(0, 100_000), 2),
            "type": rng.choice(ACCOUNT_TYPES),
        }
        for i in range(count)
    ]


def time_per_call(func, keys: list[str]) -> float:
    """Average time of one call in microseconds."""
    start = perf_counter()
    for key in keys:
        func(key)
    return (perf_counter() - start) / len(keys) * 1e6


def run_benchmark(size: int) -> tuple[float, float, float, float, float]:
    accounts = generate_accounts(size)
    rng = random.Random(size)
    keys = [rng.choice(accounts)["number"] for _ in range(LOOKUPS)]

    start = perf_counter()
    index = create_account_index(accounts)
    build_ms = (perf_counter() - start) * 1e3

    numbers_list = [a["number"] for a in accounts]
    numbers_set = set(numbers_list)

    list_search = time_per_call(lambda k: find_account_linear(accounts, k), keys)
    dict_search = time_per_call(index.get, keys)
    list_in = time_per_call(lambda k: k in numbers_list, keys)
    set_in = time_per_call(lambda k: k in numbers_set, keys)
    return list_search, dict_search, build_ms, list_in, set_in


def main() -> None:
    print(f"Середній час одного пошуку ({LOOKUPS} випадкових номерів), мкс")
    header = (f"{'records':>8} | {'list search':>11} | {'dict search':>11} | "
              f"{'speedup':>8} | {'index build, мс':>15} | {'x in list':>9} | {'x in set':>8}")
    print(header)
    print("-" * len(header))
    for size in SIZES:
        ls, ds, build, li, si = run_benchmark(size)
        print(f"{size:>8} | {ls:>11.2f} | {ds:>11.3f} | {ls / ds:>7.0f}x | "
              f"{build:>15.2f} | {li:>9.2f} | {si:>8.3f}")


if __name__ == "__main__":
    main()
