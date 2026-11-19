"""Benchmarks of the bank analytics: ``python benchmarks/benchmark.py SECTION``.

Sections:
  cpu        interest projection (CPU-bound): sequential / threads / processes / NumPy,
             3 dataset sizes, 5 runs each
  workers    scaling of ThreadPoolExecutor and ProcessPoolExecutor: 1, 2, 4, 8, 12 workers
  aggregate  replay of history + statistics: Python loops vs NumPy, 3 sizes
  io         loading 8 journal files: sequential vs ThreadPoolExecutor
  cache      lru_cache of account statistics: cold / warm, hit/miss, invalidation
  lock       race condition without Lock and the price of synchronization
Results are written to benchmarks/results/<section>.csv.
"""

from __future__ import annotations

import csv
import os
import statistics
import sys
import tempfile
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

import numpy as np

from bank_perf.analytics import (
    AccountStatistics,
    generate_dataset,
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
    project_balances_threads,
    write_journals,
)

RESULTS = Path(__file__).parent / "results"
REPEATS = 5


def measure(func: Callable[[], object], repeats: int = REPEATS) -> list[float]:
    times = []
    for _ in range(repeats):
        started = perf_counter()
        func()
        times.append(perf_counter() - started)
    return times


def peak_mb(func: Callable[[], object]) -> float:
    """Peak Python-allocated memory of one call (tracemalloc; child processes not seen)."""
    tracemalloc.start()
    func()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024 / 1024


def save(section: str, header: list[str], rows: list[list[object]]) -> None:
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / f"{section}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def fmt_runs(times: list[float]) -> str:
    return " ".join(f"{t:6.3f}" for t in times)


# ---------------------------------------------------------------- cpu
def bench_cpu() -> None:
    print(f"CPU-bound: річне нарахування відсотків (365 днів), CPU count = {os.cpu_count()}")
    print(f"{'Рахунків':>9} {'Метод':<16}{'W':>3}  {'Run 1..5, s':<35}{'Mean':>7}"
          f"{'Median':>8}{'Peak MB':>9}{'Speedup':>9}")
    rows: list[list[object]] = []
    for size in (10_000, 50_000, 100_000):
        data = generate_dataset(size, size * 5)
        balances = replay_balances_python(data)
        rates = data.rate_bp
        np_bal, np_rates = np.asarray(balances, np.int64), np.asarray(rates, np.int64)
        expected = project_balances_python(balances, rates)
        methods: list[tuple[str, int | str, Callable[[], object]]] = [
            ("Sequential", 1, lambda: project_balances_python(balances, rates)),
            ("ThreadPool", 4, lambda: project_balances_threads(balances, rates, 4)),
            ("ProcessPool", 4, lambda: project_balances_processes(balances, rates, 4)),
            ("NumPy", "-", lambda: project_balances_numpy(np_bal, np_rates)),
        ]
        baseline = 0.0
        for name, workers, func in methods:
            result = func()
            got = result.tolist() if isinstance(result, np.ndarray) else result
            assert got == expected, f"{name} gives a different result"  # correctness
            times = measure(func)
            mean = statistics.mean(times)
            baseline = baseline or mean
            peak = peak_mb(func)
            print(f"{size:>9} {name:<16}{workers!s:>3}  {fmt_runs(times):<35}{mean:7.3f}"
                  f"{statistics.median(times):8.3f}{peak:9.2f}{baseline / mean:8.2f}x")
            rows.append([size, name, workers, *[round(t, 4) for t in times], round(mean, 4),
                         round(statistics.median(times), 4), round(peak, 2),
                         round(baseline / mean, 2)])
    print("Усі реалізації дають ідентичний результат (перевірено ==).")
    save("cpu", ["accounts", "method", "workers", "run1", "run2", "run3", "run4", "run5",
                 "mean_s", "median_s", "peak_mb", "speedup"], rows)


# ---------------------------------------------------------------- workers
def bench_workers() -> None:
    size = 100_000
    data = generate_dataset(size, size * 5)
    balances, rates = replay_balances_python(data), data.rate_bp
    base = statistics.mean(measure(lambda: project_balances_python(balances, rates), 3))
    print(f"Масштабування, {size} рахунків, 3 повтори; sequential = {base:.3f} s")
    print(f"{'Workers':>7} {'ThreadPool, s':>14} {'speedup':>8} {'ProcessPool, s':>15} {'speedup':>8}")
    rows: list[list[object]] = []
    for workers in (1, 2, 4, 8, 12):
        t = statistics.mean(measure(lambda: project_balances_threads(balances, rates, workers), 3))
        p = statistics.mean(measure(lambda: project_balances_processes(balances, rates, workers), 3))
        print(f"{workers:>7} {t:14.3f} {base / t:7.2f}x {p:15.3f} {base / p:7.2f}x")
        rows.append([workers, round(t, 4), round(base / t, 2), round(p, 4), round(base / p, 2)])
    save("workers", ["workers", "threads_s", "threads_speedup", "processes_s",
                     "processes_speedup"], rows)


# ---------------------------------------------------------------- aggregate
def bench_aggregate() -> None:
    print("Агрегація історії: replay балансів + статистика сум (count/sum/mean/std/min/max)")
    print(f"{'Операцій':>9} {'Метод':<8} {'Run 1..5, s':<35}{'Mean':>7}{'Speedup':>9}")
    rows: list[list[object]] = []
    for ops in (50_000, 500_000, 2_000_000):
        data = generate_dataset(100_000, ops)
        arrays = data.as_numpy()

        def py() -> object:
            return replay_balances_python(data), transaction_stats_python(data)

        def vec() -> object:
            return replay_balances_numpy(arrays), transaction_stats_numpy(arrays)

        (b1, s1), (b2, s2) = py(), vec()  # type: ignore[misc]
        assert b1 == b2.tolist()
        assert all(abs(s1[k] - s2[k]) <= 1e-6 * max(1, abs(s1[k])) for k in s1)
        base = 0.0
        for name, func in (("Python", py), ("NumPy", vec)):
            times = measure(func)
            mean = statistics.mean(times)
            base = base or mean
            print(f"{ops:>9} {name:<8} {fmt_runs(times):<35}{mean:7.3f}{base / mean:8.2f}x")
            rows.append([ops, name, *[round(t, 4) for t in times], round(mean, 4),
                         round(base / mean, 2)])
    save("aggregate", ["operations", "method", "run1", "run2", "run3", "run4", "run5",
                       "mean_s", "speedup"], rows)


# ---------------------------------------------------------------- io
def bench_io() -> None:
    data = generate_dataset(100_000, 500_000)
    folder = Path(tempfile.mkdtemp()) / "journals"
    paths = write_journals(folder, zip(data.op_account, data.op_kind, data.op_amount), 8)
    size = sum(p.stat().st_size for p in paths) / 1024 / 1024
    print(f"I/O: 8 журналів операцій ({size:.1f} MB), 5 повторів")
    rows: list[list[object]] = []
    for latency, title in ((0.0, "локальний диск"), (0.05, "віддалене сховище, +50 мс/файл")):
        assert load_journals_threads(paths, latency) == load_journals_sequential(paths, latency)
        seq = statistics.mean(measure(lambda: load_journals_sequential(paths, latency)))
        thr = statistics.mean(measure(lambda: load_journals_threads(paths, latency, 8)))
        print(f"  {title:<32} sequential {seq:6.3f} s | ThreadPool(8) {thr:6.3f} s | "
              f"speedup {seq / thr:5.2f}x")
        rows.append([title, round(seq, 4), round(thr, 4), round(seq / thr, 2)])
    save("io", ["scenario", "sequential_s", "threads_s", "speedup"], rows)


# ---------------------------------------------------------------- cache
def bench_cache() -> None:
    data = generate_dataset(100_000, 500_000)
    stats = AccountStatistics(data)
    accounts = [7, 42, 1_001, 50_000, 99_999]
    print("Кешування статистики рахунку (lru_cache, ключ = (рахунок, версія))")
    started = perf_counter()
    for acc in accounts:
        stats.get(acc)
    cold = perf_counter() - started
    started = perf_counter()
    for _ in range(100):
        for acc in accounts:
            stats.get(acc)
    warm = (perf_counter() - started) / 100
    print(f"  cold (5 рахунків, miss)   : {cold * 1000:9.3f} ms")
    ratio = f"{cold / warm:,.0f}".replace(",", " ")
    print(f"  warm (5 рахунків, hit)    : {warm * 1000:9.3f} ms  -> speedup {ratio}x")
    print(f"  {stats.cache_info()}")
    before = stats.get(42)
    stats.add_operation(42, 0, 10_000)  # new deposit of 100.00 -> version 1
    started = perf_counter()
    after = stats.get(42)
    miss = perf_counter() - started
    print(f"  рахунок 42 до операції    : {before}")
    print(f"  після deposit 100.00      : {after}  (miss, {miss * 1000:.1f} ms)")
    stale = stats._cached(42, 0)  # what a cache without versions would return
    print(f"  кеш без invalidation дав би: {stale}  <- застаріле значення")
    print(f"  {stats.cache_info()}")
    save("cache", ["cold_ms", "warm_ms", "speedup"],
         [[round(cold * 1000, 3), round(warm * 1000, 4), round(cold / warm)]])


# ---------------------------------------------------------------- lock
def bench_lock() -> None:
    print("Синхронізація: 8 потоків, 4 x 2000 поповнень по +100 і 4 x 2000 списань по -100")
    rows: list[list[object]] = []
    for name, method in (("без Lock", SharedAccount.deposit_unsafe),
                         ("з Lock", SharedAccount.deposit_safe)):
        results = []
        for _ in range(5):
            account = SharedAccount(1_000_000)
            elapsed = hammer(account, method)
            results.append((account.balance, elapsed))
        balances = [b for b, _ in results]
        mean = statistics.mean(t for _, t in results)
        print(f"  {name:<9} очікувано 1000000, отримано {balances}  ({mean * 1000:.0f} ms)")
        rows.append([name, *balances, round(mean, 4)])
    save("lock", ["variant", "run1", "run2", "run3", "run4", "run5", "mean_s"], rows)


SECTIONS = {"cpu": bench_cpu, "workers": bench_workers, "aggregate": bench_aggregate,
            "io": bench_io, "cache": bench_cache, "lock": bench_lock}

if __name__ == "__main__":
    for section in sys.argv[1:] or list(SECTIONS):
        SECTIONS[section]()
        print()
