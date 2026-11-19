# Employee Management API

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №8, варіант 6 — асинхронний REST API обліку працівників.

## Architecture

```
HTTP client (browser, curl, EmployeeApiClient)
        │  HTTP + JSON
        ▼
FastAPI (api.py) ── Pydantic (schemas.py)
        ▼
Service layer (services.py: HRService)
        ▼
Repository layer (repositories.py)
        ▼
SQLAlchemy ORM ── SQLite (employees.db, Alembic migrations)
```

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Run

```
python -m employee_api.main --seed          # http://127.0.0.1:8000, демо-дані
uvicorn employee_api.api:app --reload       # те саме через uvicorn
```

Документація: http://127.0.0.1:8000/docs (Swagger UI), /redoc, /openapi.json.

## Endpoints

| Method | Path | Опис |
|---|---|---|
| GET | `/health` | стан сервісу |
| GET | `/employees?department_id&position&search&min_salary&max_salary&sort_by_salary&limit&offset` | список, пошук, фільтрація |
| GET | `/employees/{id}` | працівник |
| POST | `/employees` | прийняти працівника |
| PATCH | `/employees/{id}` | змінити ПІБ, посаду, зарплату, відділ, дату прийому |
| DELETE | `/employees/{id}` | звільнити |
| GET / POST | `/departments` | відділи |
| GET | `/departments/{id}/employees` | працівники відділу |
| GET | `/departments/{id}/statistics` | кількість, фонд, середня, min/max зарплата |
| POST | `/departments/{id}/raise` | масове підвищення зарплат (одна транзакція) |
| POST | `/departments/statistics` | статистика кількох відділів паралельно |
| GET | `/stats` | підсумок по підприємству |

## Async client

```
python -m employee_api.external_api --concurrency 3 1 2 3 4 5 42
python experiments\async_experiments.py
```

`EmployeeApiClient` (httpx.AsyncClient): `asyncio.Task` + `gather`, Semaphore, timeout,
retry з exponential backoff для мережевих помилок і 429/5xx.

## Tests

```
pytest -v
```

## Author

Student: Дораж Михайло
Group: ФеП-31
