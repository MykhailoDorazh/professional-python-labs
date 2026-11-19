# Employee App — test suite

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №6, варіант 6 — автоматизоване тестування системи обліку працівників.

Production code поєднує результати ЛР №4 (типізована модель `Employee`,
`Manager`, `Developer`, `Department`, `PayrollRecord`, `Money`, repository,
Protocols, `HRService`, `PayrollService`) і ЛР №5 (YAML-конфігурація відділів і
мінімальної зарплати, CSV import, atomic JSON export), додає сервіс звітів
(`ReportService` + `ReportPublisher`) та асинхронний payroll provider
(`AsyncPayrollService`).

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Tests

```
pytest -v --cov=employee_app --cov-branch --cov-report=term-missing --cov-report=html
pytest -m "not integration"     # лише unit tests
pytest -m integration           # лише integration tests
pytest tests/unit/test_models.py::test_salary_boundaries
```

Coverage threshold (`fail_under = 85`) і branch coverage задані в `pyproject.toml`.

## Structure

- `tests/conftest.py` — shared fixtures (factory, parameterized, autouse, yield);
- `tests/unit/` — unit tests моделей, сервісів, конфігурації, імпорту, експорту, звітів, async;
- `tests/integration/` — CSV → validation → departments → JSON + report, main(), async flow;
- `experiments/` — weak/strong tests, branch coverage, mock vs fake, flaky tests.

## Author

Student: Дораж Михайло
Group: ФеП-31
