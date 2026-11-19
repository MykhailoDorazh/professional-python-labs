# Bank DB — persistence layer

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №7, варіант 4 — система банківських рахунків з базою даних SQLite.

## Features

- SQLite + SQLAlchemy 2.0 ORM: `clients` 1─N `accounts` 1─N `transactions`;
- PRIMARY KEY, FOREIGN KEY (`ON DELETE CASCADE`, `PRAGMA foreign_keys=ON`), UNIQUE, CHECK
  (`balance_cents >= 0`, `amount_cents > 0`);
- Repository Pattern (`ClientRepository`, `AccountRepository`, `TransactionRepository`,
  generic `SqlAlchemyRepository[T]`) і Service Layer (`BankService`);
- атомарний `transfer_money()` з COMMIT/ROLLBACK (`database.transaction` — unit of work);
- DB-API (`sqlite3`) — параметризований пошук за номером рахунку;
- Alembic: `0001` — початкова схема, `0002` — колонка `account_type` (upgrade/downgrade);
- integration tests на окремій тестовій БД (`tmp_path`).

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Database & migrations

```
alembic upgrade head        # створити/оновити bank.db
alembic current
alembic history
alembic downgrade -1
```

URL бази можна змінити змінною `BANK_DATABASE_URL` (за замовчуванням `sqlite:///bank.db`).

## Run

```
python -m bank_db.main            # демонстрація CRUD, transfer, звітів, DB-API (demo.db)
python -m bank_db.main --echo     # те саме + SQL, згенерований для transfer
python experiments/sql_injection.py
python experiments/acid_demo.py
```

## Tests

```
pytest -v
```

## Author

Student: Дораж Михайло
Group: ФеП-31
