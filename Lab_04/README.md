# Employee Domain

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №4, варіант 6 — «Облік працівників»:
типізована об'єктна модель предметної області.

## Domain

- `Employee` → `Manager`, `Developer` — працівники (поліморфний `bonus()`);
- `Department` (dataclass) — відділ, колекція своїх працівників;
- `PayrollRecord` (frozen dataclass) — рядок нарахування зарплати;
- `Money`, `EmployeeId` (frozen value objects);
- `InMemoryRepository[T]` — generic repository;
- `Notifier`, `HasKey`, `EmployeeReader`, `EmployeeStore` — Protocols;
- `ReportFormatter` (ABC) → `TextReport`, `JsonReport` — абстракція звітів;
- `HRService`, `PayrollService` — application layer;
- `EmployeePayload`, `SummaryPayload` — TypedDict для зовнішніх даних.

Реалізовано додавання працівника з призначенням відділу, пошук за відділом,
середню і максимальну зарплату, фонд оплати праці, зміну окладу, переведення
між відділами, нарахування за місяць, repository, notifier і report abstractions.

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Run

```
python -m employee_domain.main
mypy src
python -m unittest discover tests
python experiments/di_comparison.py
python experiments/composition_vs_inheritance.py
mypy experiments/type_errors.py        # 3 навмисні помилки типів
mypy experiments/type_errors_fixed.py  # виправлений варіант
```

## Author

Student: Дораж Михайло
Group: ФеП-31
