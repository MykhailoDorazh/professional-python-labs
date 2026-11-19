# Bank Analytics

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №2, варіант 4 — «Аналіз системи банківських рахунків».
Продовжує проєкт лабораторної роботи №1 (система банківських рахунків).

## Description

Модуль обробки структурованих даних (рахунок = dict з полями
`number`, `client`, `balance`, `type`):

- пошук рахунку за номером: лінійний у list і через dict-index;
- групування рахунків за типом (`defaultdict`), вкладене групування;
- кількість рахунків за типом (`Counter`);
- загальна сума коштів, середній баланс, рахунок із найбільшим балансом;
- фільтрація за мінімальним балансом (closure), сортування за балансом;
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
python -m bank_analytics.main
python -m bank_analytics.benchmark
python -m unittest discover tests -v
```

## Project structure

- `src/bank_analytics/data.py` — вхідні дані (list of dicts, tuple типів).
- `src/bank_analytics/decorators.py` — `measure_time`, `log_operation`.
- `src/bank_analytics/processors.py` — пошук, index, групування, фільтри, сортування.
- `src/bank_analytics/analytics.py` — агрегація, `*args`, `**kwargs`, експорт.
- `src/bank_analytics/benchmark.py` — порівняння швидкості структур даних.
- `src/bank_analytics/main.py` — точка входу.

## Author

Student: Дораж Михайло
Group: ФеП-31
