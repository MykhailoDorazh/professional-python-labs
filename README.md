# Employee DB — persistence layer

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №7, варіант 6 — облік працівників з базою даних SQLite.

## Features

- SQLite + SQLAlchemy 2.0 ORM: `departments` 1─N `employees`;
- PRIMARY KEY, FOREIGN KEY (`ON DELETE RESTRICT`, `PRAGMA foreign_keys=ON`), UNIQUE, CHECK
  (`0 <= salary_cents <= 100000000`, непорожнє ПІБ);
- Repository Pattern (`DepartmentRepository`, `EmployeeRepository`, generic
  `SqlAlchemyRepository[T]`) і Service Layer (`HRService`);
- CRUD працівників і відділів, зміна посади/зарплати, переведення між відділами;
- список, пошук за відділом, середня і максимальна зарплата, фонд оплати праці (SQL);
- атомарні масові операції з COMMIT/ROLLBACK: `transfer_many()`, `raise_salaries()`;
- DB-API (`sqlite3`) — параметризований пошук за відділом, масове підвищення з rollback;
- Alembic: `0001` — початкова схема, `0002` — колонка `hire_date` (upgrade/downgrade);
- integration tests на окремій тестовій БД (`tmp_path`).

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Database & migrations

```
alembic upgrade head        # створити/оновити employees.db
alembic current
alembic history
alembic downgrade -1
```

URL бази можна змінити змінною `EMPLOYEE_DATABASE_URL` (за замовчуванням
`sqlite:///employees.db`).

## Run

```
python -m employee_db.main          # демонстрація CRUD, транзакцій, звітів, DB-API (demo.db)
python -m employee_db.main --echo   # те саме + SQL масового підвищення зарплат
python experiments/sql_injection.py
python experiments/acid_demo.py
python experiments/show_db.py demo.db
```

## Tests

```
pytest -v
```

## Author

Student: Дораж Михайло
Group: ФеП-31
