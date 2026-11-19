# Bank App — test suite

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №6, варіант 4 — автоматизоване тестування системи банківських рахунків.

Production code поєднує результати ЛР №4 (типізована модель `Account`,
`SavingsAccount`, `CurrentAccount`, `Customer`, `Transaction`, `Money`,
repository, Protocols) і ЛР №5 (YAML-конфігурація, CSV import, atomic JSON export)
та додає асинхронні залежності (`AsyncPayoutService`, `CurrencyConverter`).

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Tests

```
pytest -v --cov=bank_app --cov-branch --cov-report=term-missing --cov-report=html
pytest -m "not integration"     # лише unit tests
pytest -m integration           # лише integration tests
pytest tests/unit/test_models.py::test_withdraw_boundary
```

Coverage threshold (`fail_under = 85`) і branch coverage задані в `pyproject.toml`.

## Structure

- `tests/conftest.py` — shared fixtures (factory, parameterized, autouse, yield);
- `tests/unit/` — unit tests моделей, сервісів, конфігурації, імпорту, експорту, async;
- `tests/integration/` — CSV → validation → domain → JSON, main(), async flow;
- `experiments/` — weak/strong tests, branch coverage, mock vs fake, flaky tests.

## Author

Student: Дораж Михайло
Group: ФеП-31
