"""Threads and processes: CPU-bound projection, I/O-bound journal loading, Lock."""

from __future__ import annotations

import csv
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from bank_perf.analytics import project_chunk


def split(balances: list[int], rates: list[int], parts: int) -> list[tuple[list[int], list[int]]]:
    """Contiguous chunks: few large tasks keep pickling/IPC overhead low."""
    size = -(-len(balances) // parts)  # ceil division
    return [(balances[i:i + size], rates[i:i + size]) for i in range(0, len(balances), size)]


def _project_with(executor: Executor, balances: list[int], rates: list[int],
                  chunks: int) -> list[int]:
    result: list[int] = []
    for part in executor.map(project_chunk, split(balances, rates, chunks)):
        result.extend(part)  # map() keeps the order of chunks
    return result


def project_balances_threads(balances: list[int], rates: list[int], workers: int = 4) -> list[int]:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return _project_with(executor, balances, rates, workers)


def project_balances_processes(balances: list[int], rates: list[int],
                               workers: int = 4) -> list[int]:
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return _project_with(executor, balances, rates, workers)


def project_balances_threading(balances: list[int], rates: list[int],
                               workers: int = 4) -> list[int]:
    """Low-level variant with threading.Thread, start() and join()."""
    chunks = split(balances, rates, workers)
    results: list[list[int]] = [[] for _ in chunks]

    def worker(index: int) -> None:
        results[index] = project_chunk(chunks[index])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(chunks))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return [value for part in results for value in part]


# ---------- I/O-bound: journals of operations ----------
def write_journals(folder: Path, rows: Iterable[tuple[int, int, int]], files: int) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = [folder / f"journal_{i:02d}.csv" for i in range(files)]
    handles = [path.open("w", newline="", encoding="utf-8") for path in paths]
    writers = [csv.writer(h) for h in handles]
    for w in writers:
        w.writerow(["account", "kind", "amount"])
    for n, row in enumerate(rows):
        writers[n % files].writerow(row)
    for h in handles:
        h.close()
    return paths


def load_journal(path: Path, latency: float = 0.0) -> int:
    """Read one journal; `latency` simulates remote storage (network round trip)."""
    if latency:
        time.sleep(latency)  # waiting for I/O releases the GIL
    with path.open(encoding="utf-8") as f:
        return sum(1 for _ in f) - 1


def load_journals_sequential(paths: list[Path], latency: float = 0.0) -> list[int]:
    return [load_journal(p, latency) for p in paths]


def load_journals_threads(paths: list[Path], latency: float = 0.0, workers: int = 8) -> list[int]:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(lambda p: load_journal(p, latency), paths))


# ---------- synchronization ----------
class SharedAccount:
    """In-memory account changed by many threads.

    `deposit_unsafe` is a read-modify-write without a lock: the explicit
    `time.sleep(0)` gives the scheduler a chance to switch threads between
    reading and writing, which is exactly where a race condition happens.
    """

    def __init__(self, balance: int) -> None:
        self.balance = balance
        self.lock = threading.Lock()
        self.operations = 0

    def deposit_unsafe(self, amount: int) -> None:
        current = self.balance
        time.sleep(0)
        self.balance = current + amount
        self.operations += 1

    def deposit_safe(self, amount: int) -> None:
        with self.lock:  # critical section: one thread at a time
            current = self.balance
            time.sleep(0)
            self.balance = current + amount
            self.operations += 1


def hammer(account: SharedAccount, method: Callable[[SharedAccount, int], None],
           threads: int = 8, rounds: int = 2_000) -> float:
    """Half of the threads deposit +100, the other half withdraw -100 `rounds` times.

    The same number of deposits and withdrawals: the final balance must not change.
    """
    def work(amount: int) -> None:
        for _ in range(rounds):
            method(account, amount)

    pool = [threading.Thread(target=work, args=(100 if i % 2 == 0 else -100,))
            for i in range(threads)]
    started = time.perf_counter()
    for t in pool:
        t.start()
    for t in pool:
        t.join()
    return time.perf_counter() - started
