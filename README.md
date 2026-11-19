# Bank Accounts API

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №8, варіант 4 — асинхронний REST API системи банківських рахунків.

## Architecture

```
HTTP client (browser, curl, BankApiClient)
        │  HTTP + JSON
        ▼
FastAPI (api.py) ── Pydantic (schemas.py)
        ▼
Service layer (services.py: BankService)
        ▼
Repository layer (repositories.py)
        ▼
SQLAlchemy ORM ── SQLite (bank.db, Alembic migrations)
```

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Run

```
python -m bank_api.main --seed            # http://127.0.0.1:8000, демо-дані
uvicorn bank_api.api:app --reload         # те саме через uvicorn
```

Документація: http://127.0.0.1:8000/docs (Swagger UI), /redoc, /openapi.json.

## Endpoints

| Method | Path | Опис |
|---|---|---|
| GET | `/health` | стан сервісу |
| POST | `/clients` | створити клієнта |
| GET | `/clients/{id}`, `/clients/{id}/accounts` | клієнт і його рахунки |
| POST | `/accounts` | відкрити рахунок |
| GET | `/accounts?client_id&number&min_balance&account_type&sort_by_balance&limit&offset` | пошук і фільтрація |
| GET / PATCH / DELETE | `/accounts/{id}` | рахунок, зміна типу, закриття |
| GET | `/accounts/{id}/transactions?kind=` | історія операцій |
| POST | `/accounts/{id}/deposit`, `/accounts/{id}/withdraw` | поповнення, списання |
| POST | `/transfers` | атомарний переказ |
| GET | `/stats` | загальна сума коштів, оборот |
| POST | `/accounts/overview` | баланси й історія кількох рахунків паралельно |

## Async client

```
python -m bank_api.external_api --concurrency 3 1 2 3 4 5 99
python experiments\async_experiments.py
```

`BankApiClient` (httpx.AsyncClient): `asyncio.Task` + `gather`, Semaphore, timeout,
retry з exponential backoff для мережевих помилок і 429/5xx.

## Tests

```
pytest -v
```

## Author

Student: Дораж Михайло
Group: ФеП-31
