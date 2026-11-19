"""cProfile and tracemalloc of the baseline report.

``python -m bank_perf.profiling cpu``    — cProfile of build_report()
``python -m bank_perf.profiling memory`` — tracemalloc: lists vs NumPy arrays
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

from bank_perf.analytics import (
    build_report,
    build_report_optimized,
    generate_dataset,
    replay_balances_numpy,
    replay_balances_python,
)

ACCOUNTS, OPERATIONS = 100_000, 500_000


def profile_cpu(accounts: int = ACCOUNTS, operations: int = OPERATIONS) -> None:
    data = generate_dataset(accounts, operations)
    profiler = cProfile.Profile()
    started = perf_counter()
    profiler.enable()
    build_report(data)
    profiler.disable()
    total = perf_counter() - started
    print(f"build_report(): {sp(accounts)} рахунків, {sp(operations)} операцій, "
          f"{total:.2f} s (під cProfile)")
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs().sort_stats("cumulative").print_stats(10)
    lines = stream.getvalue().splitlines()
    start = next(i for i, line in enumerate(lines) if "ncalls" in line)
    print("\n".join(line for line in lines[start - 2:] if line.strip()))

    optimized = perf_counter()
    build_report_optimized(data)
    print(f"build_report_optimized() (NumPy): {perf_counter() - optimized:.2f} s")


def sp(number: int) -> str:
    return f"{number:,}".replace(",", " ")


def mb(value: int) -> str:
    return f"{value / 1024 / 1024:8.2f} MB"


def profile_memory(accounts: int = ACCOUNTS, operations: int = OPERATIONS) -> None:
    tracemalloc.start()
    data = generate_dataset(accounts, operations)
    lists_current, lists_peak = tracemalloc.get_traced_memory()
    snapshot = tracemalloc.take_snapshot()
    print(f"Dataset як Python lists : current {mb(lists_current)}, peak {mb(lists_peak)}")
    print("  Top-3 рядки за обсягом пам'яті:")
    for stat in snapshot.statistics("lineno")[:3]:
        frame = stat.traceback[0]
        print(f"    {Path(frame.filename).name}:{frame.lineno:<4} {mb(stat.size)}"
              f"  ({sp(stat.count)} об'єктів)")

    tracemalloc.reset_peak()
    before, _ = tracemalloc.get_traced_memory()
    arrays = data.as_numpy()
    after, peak = tracemalloc.get_traced_memory()
    print(f"Ті самі дані як NumPy int64: +{mb(after - before)} (peak конвертації {mb(peak - before)})")

    runs: list[tuple[str, Callable[[], object]]] = [
        ("replay_balances_python", lambda: replay_balances_python(data)),
        ("replay_balances_numpy ", lambda: replay_balances_numpy(arrays)),
    ]
    for name, run in runs:
        tracemalloc.reset_peak()
        base, _ = tracemalloc.get_traced_memory()
        result = run()
        _, peak = tracemalloc.get_traced_memory()
        print(f"Peak під час {name}: {mb(peak - base)}")
        del result
    tracemalloc.stop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("what", choices=["cpu", "memory"])
    parser.add_argument("--accounts", type=int, default=ACCOUNTS)
    parser.add_argument("--operations", type=int, default=OPERATIONS)
    args = parser.parse_args(argv)
    if args.what == "cpu":
        profile_cpu(args.accounts, args.operations)
    else:
        profile_memory(args.accounts, args.operations)


if __name__ == "__main__":
    main()
