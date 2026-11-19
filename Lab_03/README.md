# Bank Stream

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №3, варіант 4 — «Потокова обробка системи банківських рахунків».
Продовжує проєкти лабораторних робіт №1 і №2.

## Input

CSV: `account_number,client,balance,operation,amount`

Кожен рядок — рахунок (`UA` + 8 цифр), клієнт, поточний баланс і операція
(`deposit` / `withdraw`) з сумою, яку потрібно застосувати.

## Pipeline

```
CSV -> read_lines() -> clean_lines() -> parse_csv_rows() -> validate_operations()
    -> filter_by_client() -> normalize_clients() -> apply_operations()
    -> filter_by_balance() -> batched() / calculate_statistics() -> report
```

Усі етапи — генератори: записи проходять конвеєр по одному, пам'ять не
залежить від розміру файла. Списання, після якого баланс став би
від'ємним, відхиляється.

## Requirements

Python 3.11+

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

## Run

```
python -m bank_stream.generate 100000        # test data set data/operations_100000.csv
python -m bank_stream.main                   # pipeline demo
python -m bank_stream.experiment             # eager vs lazy: time, memory, early termination
python -m unittest discover tests -v
```

## Project structure

- `readers.py` — `read_lines`, `read_many` (chain), own iterator `RecordFile`.
- `parsers.py` — cleaning, CSV parsing, validation.
- `filters.py` — filters by client and balance, lazy search.
- `transformations.py` — applying deposits/withdrawals, normalization.
- `batches.py` — batching (islice), batch summary (groupby).
- `analytics.py` — one-pass statistics, accumulate.
- `pipeline.py` — building the pipeline, stage logging.
- `generate.py`, `experiment.py`, `utils.py`, `main.py`.

## Author

Student: Дораж Михайло
Group: ФеП-31
