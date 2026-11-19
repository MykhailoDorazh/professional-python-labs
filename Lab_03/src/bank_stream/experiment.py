"""Eager vs lazy experiment: elapsed time, peak memory, time to first result,
early termination (python -m bank_stream.experiment)."""

import csv
import gc
import tracemalloc
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

from bank_stream.analytics import calculate_statistics
from bank_stream.filters import find_first
from bank_stream.generate import dataset_path, generate_file
from bank_stream.models import ProcessedOperation
from bank_stream.parsers import validate_operations
from bank_stream.pipeline import build_pipeline
from bank_stream.transformations import apply_operation

SIZES: tuple[int, ...] = (10_000, 100_000, 500_000)
EARLY_SIZE: int = 1_000_000


def big_rejected_withdrawal(record: ProcessedOperation) -> bool:
    """Condition for 'first result': withdrawal of more than 15 000 rejected."""
    return not record.accepted and record.amount > 15_000


def rare_condition(record: ProcessedOperation) -> bool:
    """Condition for early termination test."""
    return record.client == "Юлія Олійник" and record.balance_after > 99_000


# ---------- eager: усі проміжні результати зберігаються у lists ----------

def read_all_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def eager_processed(path: Path) -> list[ProcessedOperation]:
    rows = read_all_rows(path)
    valid = list(validate_operations(rows))
    return [apply_operation(op) for op in valid]


def eager_statistics(path: Path) -> dict[str, Any]:
    return calculate_statistics(eager_processed(path))


def eager_first(path: Path) -> ProcessedOperation | None:
    return find_first(eager_processed(path), big_rejected_withdrawal)


# ---------- lazy: записи проходять конвеєр по одному ----------

def lazy_statistics(path: Path) -> dict[str, Any]:
    return calculate_statistics(build_pipeline(path))


def lazy_first(path: Path) -> ProcessedOperation | None:
    return find_first(build_pipeline(path), big_rejected_withdrawal)


# ---------- вимірювання ----------

def measure_time(function: Callable, *args: Any, repeat: int = 1) -> tuple[Any, float]:
    """Best elapsed time of `repeat` runs, seconds."""
    best, result = float("inf"), None
    for _ in range(repeat):
        gc.collect()
        start = perf_counter()
        result = function(*args)
        best = min(best, perf_counter() - start)
    return result, best


def measure_peak_memory(function: Callable, *args: Any) -> tuple[Any, int]:
    """Peak memory allocated during the call (tracemalloc), bytes.
    The function must consume the generator, otherwise only the creation
    of a generator object would be measured."""
    gc.collect()
    tracemalloc.start()
    result = function(*args)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, peak


def mb(value: int) -> str:
    return f"{value / 2**20:.2f} MB"


def ensure_dataset(size: int) -> Path:
    path = dataset_path(size)
    if not path.exists():
        generate_file(path, size)
    return path


def run_main_experiment() -> None:
    print("Eager vs lazy: повна статистика (час - найкращий із 3 запусків)")
    print(f"{'records':>8} | {'eager time':>10} | {'lazy time':>9} | {'eager peak':>11} | "
          f"{'lazy peak':>9} | {'eager 1st':>9} | {'lazy 1st':>9}")
    print("-" * 85)
    for size in SIZES:
        path = ensure_dataset(size)
        repeat = 3 if size <= 100_000 else 1
        eager_res, eager_t = measure_time(eager_statistics, path, repeat=repeat)
        lazy_res, lazy_t = measure_time(lazy_statistics, path, repeat=repeat)
        assert eager_res == lazy_res, "eager and lazy results differ"
        _, eager_mem = measure_peak_memory(eager_statistics, path)
        _, lazy_mem = measure_peak_memory(lazy_statistics, path)
        first_e, eager_f = measure_time(eager_first, path)
        first_l, lazy_f = measure_time(lazy_first, path)
        assert first_e == first_l
        print(f"{size:>8} | {eager_t:>8.3f} s | {lazy_t:>7.3f} s | {mb(eager_mem):>11} | "
              f"{mb(lazy_mem):>9} | {eager_f * 1e3:>6.0f} ms | {lazy_f * 1e3:>6.2f} ms")
        funds = f"{lazy_res['total_funds']:,.2f}".replace(",", " ")
        print(f"{'':>8}   valid records: {lazy_res['count']}, total funds: {funds}")


def run_early_termination() -> None:
    path = ensure_dataset(EARLY_SIZE)
    print(f"\nEarly termination, {EARLY_SIZE} records, умова: "
          "клієнт 'Юлія Олійник' і баланс > 99 000")

    def lazy() -> tuple[ProcessedOperation | None, int]:
        stats: Counter[str] = Counter()
        return find_first(build_pipeline(path, stats=stats), rare_condition), stats["rows"]

    def eager() -> ProcessedOperation | None:
        matches = [r for r in build_pipeline(path) if rare_condition(r)]
        return matches[0] if matches else None

    (found, rows_read), lazy_t = measure_time(lazy)
    found_e, eager_t = measure_time(eager)
    assert found == found_e
    print(f"  знайдено: {found.account_number} {found.client} {found.balance_after:.2f}")
    print(f"  lazy  find_first: {lazy_t * 1e3:8.1f} ms, прочитано рядків: {rows_read}")
    print(f"  eager filtered list: {eager_t * 1e3:8.1f} ms, прочитано рядків: {EARLY_SIZE}")


def main() -> None:
    run_main_experiment()
    run_early_termination()


if __name__ == "__main__":
    main()
