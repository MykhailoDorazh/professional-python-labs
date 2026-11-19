"""Charts from benchmarks/results/*.csv: execution time and speedup."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).parent / "results"


def read(name: str) -> list[dict[str, str]]:
    with (RESULTS / f"{name}.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_cpu() -> None:
    rows = read("cpu")
    sizes = sorted({int(r["accounts"]) for r in rows})
    methods = ["Sequential", "ThreadPool", "ProcessPool", "NumPy"]
    colors = ["#8c8c8c", "#e3a33b", "#3b7de3", "#2fa35b"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    width = 0.2
    for i, (method, color) in enumerate(zip(methods, colors, strict=True)):
        values = [next(float(r["median_s"]) for r in rows
                       if r["method"] == method and int(r["accounts"]) == s) for s in sizes]
        xs = [k + (i - 1.5) * width for k in range(len(sizes))]
        bars = ax.bar(xs, values, width, label=method, color=color)
        ax.bar_label(bars, fmt="%.2f", fontsize=7, padding=1)
    ax.set_xticks(range(len(sizes)), [f"{s:,}".replace(",", " ") + " рахунків" for s in sizes])
    ax.set_ylabel("Медіана часу, s (5 повторів)")
    ax.set_title("Нарахування відсотків за рік: час виконання")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "time_projection.png", dpi=130)


def plot_workers() -> None:
    rows = read("workers")
    workers = [int(r["workers"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(workers, [float(r["processes_speedup"]) for r in rows], "o-", color="#3b7de3",
            label="ProcessPoolExecutor")
    ax.plot(workers, [float(r["threads_speedup"]) for r in rows], "s-", color="#e3a33b",
            label="ThreadPoolExecutor")
    ax.plot(workers, workers, ":", color="#999999", label="ідеальне (лінійне)")
    for w, r in zip(workers, rows, strict=True):
        ax.annotate(f"{float(r['processes_speedup']):.2f}x", (w, float(r["processes_speedup"])),
                    textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
    ax.set_xticks(workers)
    ax.set_ylim(0, max(workers) + 0.5)
    ax.set_xlabel("Кількість workers")
    ax.set_ylabel("Speedup відносно sequential")
    ax.set_title("Масштабування: 100 000 рахунків")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "speedup_workers.png", dpi=130)


if __name__ == "__main__":
    plot_cpu()
    plot_workers()
    print("saved", RESULTS / "time_projection.png", RESULTS / "speedup_workers.png")
