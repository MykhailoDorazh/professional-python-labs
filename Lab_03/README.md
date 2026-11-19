# Employee Stream

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №3, варіант 6 — «Потокова обробка даних працівників».
Продовжує проєкти лабораторних робіт №1 і №2.

## Input

CSV: `employee_id,name,position,department,salary`

Кожен рядок — працівник (`E` + 6 цифр), ПІБ, посада, відділ і місячна зарплата.

## Pipeline

```
CSV -> read_lines() -> clean_lines() -> parse_csv_rows() -> validate_employees()
    -> normalize() -> filter_by_department() -> filter_by_salary()
    -> calculate_statistics() / batched() / export_batches() -> report
```

Усі етапи — генератори: записи проходять конвеєр по одному, пам'ять не
залежить від розміру файла. Некоректні записи (табельний номер, порожні поля,
зарплата < 0 або нечислова) відкидаються під час читання і підраховуються.

## Features

- streaming validation записів працівників;
- фільтрація за відділом, lazy filter за рівнем зарплати;
- streaming average salary, працівник із максимальною зарплатою;
- потоковий фонд оплати праці, накопичений фонд (accumulate);
- підрахунок працівників за відділами (Counter);
- batch processing (islice, groupby) і batch export у CSV-файли;
- eager vs lazy experiment: час, пам'ять, перший результат, early termination.

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
python -m employee_stream.generate 100000   # test data set data/employees_100000.csv
python -m employee_stream.main              # pipeline demo
python -m employee_stream.experiment        # eager vs lazy
python -m unittest discover tests -v
```

## Project structure

- `readers.py` — `read_lines`, `read_many` (chain), own iterator `RecordFile`.
- `parsers.py` — cleaning, CSV parsing, streaming validation.
- `filters.py` — filters by department and salary level, lazy search.
- `transformations.py` — normalisation of names and departments.
- `batches.py` — batching (islice), batch summary (groupby), batch export.
- `analytics.py` — one-pass statistics, payroll, average, max, accumulate.
- `pipeline.py` — building the pipeline, stage logging.
- `generate.py`, `experiment.py`, `utils.py`, `main.py`.

## Author

Student: Дораж Михайло
Group: ФеП-31
