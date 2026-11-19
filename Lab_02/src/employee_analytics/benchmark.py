"""Benchmark: search in list vs dict-index, membership in list vs set."""

import random
from time import perf_counter

from employee_analytics.data import DEPARTMENTS
from employee_analytics.processors import create_employee_index, find_employee_linear

SIZES: tuple[int, ...] = (1_000, 10_000, 100_000)
LOOKUPS: int = 500


def generate_employees(count: int, seed: int = 42) -> list[dict]:
    """Synthetic data set of `count` employees (list comprehension)."""
    rng = random.Random(seed)
    return [
        {
            "id": f"E{100_000 + i:07d}",
            "name": f"Працівник {i}",
            "position": rng.choice(("Розробник", "Аналітик", "Менеджер", "Бухгалтер")),
            "department": rng.choice(DEPARTMENTS),
            "salary": round(rng.uniform(15_000, 120_000), 2),
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
    employees = generate_employees(size)
    rng = random.Random(size)
    keys = [rng.choice(employees)["id"] for _ in range(LOOKUPS)]

    start = perf_counter()
    index = create_employee_index(employees)
    build_ms = (perf_counter() - start) * 1e3

    ids_list = [e["id"] for e in employees]
    ids_set = set(ids_list)

    list_search = time_per_call(lambda k: find_employee_linear(employees, k), keys)
    dict_search = time_per_call(index.get, keys)
    list_in = time_per_call(lambda k: k in ids_list, keys)
    set_in = time_per_call(lambda k: k in ids_set, keys)
    return list_search, dict_search, build_ms, list_in, set_in


def main() -> None:
    print(f"Середній час одного пошуку ({LOOKUPS} випадкових табельних номерів), мкс")
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
