# Employee Analytics

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №2, варіант 6 — «Аналіз даних працівників».
Продовжує проєкт лабораторної роботи №1 (система обліку працівників).

## Description

Модуль обробки структурованих даних (працівник = dict з полями
`id`, `name`, `position`, `department`, `salary`):

- пошук працівника за табельним номером: лінійний у list і через dict-index;
- групування працівників за відділом (`defaultdict`), вкладене групування відділ → посада;
- кількість працівників за відділом (`Counter`), унікальні посади (`set`);
- фонд оплати праці, середня зарплата, працівник із максимальною зарплатою;
- фільтрація за мінімальною зарплатою (closure), сортування за зарплатою;
- універсальні filter / sort, конвеєр обробки, експорт зведення в JSON;
- decorators: вимірювання часу та історія операцій (`deque`);
- benchmark: list vs dict, list vs set.

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
python -m employee_analytics.main
python -m employee_analytics.benchmark
python -m unittest discover tests -v
```

## Project structure

- `src/employee_analytics/data.py` — вхідні дані (list of dicts, tuple відділів).
- `src/employee_analytics/decorators.py` — `measure_time`, `log_operation`.
- `src/employee_analytics/processors.py` — пошук, index, групування, фільтри, сортування.
- `src/employee_analytics/analytics.py` — агрегація, `*args`, `**kwargs`, експорт.
- `src/employee_analytics/benchmark.py` — порівняння швидкості структур даних.
- `src/employee_analytics/main.py` — точка входу.

## Author

Student: Дораж Михайло
Group: ФеП-31
