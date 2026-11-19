# Bank Domain

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №4, варіант 4 — «Система банківських рахунків»:
типізована об'єктна модель предметної області.

## Domain

- `Account` (ABC) → `SavingsAccount`, `CurrentAccount` — рахунки;
- `Customer` (dataclass) — клієнт;
- `Transaction` (frozen dataclass) — запис операції;
- `Money`, `AccountNumber` (frozen value objects);
- `InMemoryRepository[T]` — generic repository;
- `Notifier`, `HasKey`, `AccountReader`, `AccountStore` — Protocols;
- `BankService`, `ReportService` — application layer;
- `AccountPayload`, `SummaryPayload` — TypedDict для зовнішніх даних.

Реалізовано deposit, withdraw із забороною від'ємного балансу, перевірку
балансу, пошук рахунку, загальну суму коштів, repository і notification Protocol.

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Run

```
python -m bank_domain.main
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
