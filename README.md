# Bank Perf — profiling and optimization

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №9, варіант 4 — профілювання та оптимізація аналітики системи
банківських рахунків (продовження ЛР №7–8: SQLite + REST API).

## New modules

- `analytics.py` — синтетичний набір даних (100 000+ рахунків, 500 000+ операцій),
  baseline на Python-циклах і NumPy-версії: replay балансів, статистика операцій,
  річне нарахування відсотків (CPU-bound), `AccountStatistics` з `lru_cache` та invalidation;
- `parallel.py` — `threading.Thread`, `ThreadPoolExecutor`, `ProcessPoolExecutor`,
  паралельне читання журналів (I/O-bound), `SharedAccount` з race condition і `Lock`;
- `profiling.py` — cProfile і tracemalloc;
- `benchmarks/benchmark.py` — серії вимірювань (5 повторів), CSV у `benchmarks/results/`,
  `benchmarks/plot.py` — графіки часу і speedup.

## Usage

```
python -m pip install -e ".[dev]"
python -m bank_perf.profiling cpu
python -m bank_perf.profiling memory
python benchmarks\benchmark.py               # усі секції (~10 хв)
python benchmarks\benchmark.py cpu workers   # окремі секції
python benchmarks\plot.py
pytest -v
```

## Author

Student: Дораж Михайло
Group: ФеП-31
