# Bank Account Service

Production-oriented REST API системи банківських рахунків.
Навчальний проєкт з дисципліни «Професійний Python», варіант 4, лабораторна робота №10 —
фінальна версія проєкту, що розвивався в ЛР №1–9.

## Description

Сервіс зберігає клієнтів, їхні рахунки та історію операцій у реляційній базі (SQLite за
замовчуванням), виконує поповнення, списання й атомарні перекази без від'ємного балансу і
надає все це через REST API на FastAPI з автоматичною документацією OpenAPI.

## Features

- клієнти, рахунки (`current` / `savings`), історія операцій;
- поповнення, списання, атомарний переказ (`transfer_money()` — COMMIT або ROLLBACK);
- CHECK / UNIQUE / FOREIGN KEY у БД, Alembic-міграції (застосовуються при старті контейнера);
- загальна сума коштів, оборот, паралельний огляд кількох рахунків (asyncio + Semaphore);
- прогноз коштів через рік з щоденною капіталізацією (NumPy — переможець бенчмарку ЛР №9);
- конфігурація лише через environment variables / `.env` (pydantic-settings);
- secrets (`API_KEY`) не зберігаються в коді, Git чи Docker image;
- `/health` перевіряє і процес, і доступність бази (200 / 503);
- structured logging без `print()`, рівень з `LOG_LEVEL`;
- wheel + sdist, multi-stage Docker image, non-root user, HEALTHCHECK, volume для БД;
- GitHub Actions: ruff, ruff format, mypy --strict, pytest + coverage ≥ 85 %, build, docker.

## Requirements

- Python 3.12+ (перевірено на 3.12 і 3.13)
- Docker 24+ (для контейнера)

## Installation

```
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Configuration

```
copy .env.example .env            # Linux/macOS: cp .env.example .env
```

| Variable | Default | Опис |
|---|---|---|
| `APP_ENV` | `development` | `development` / `test` / `production` |
| `DATABASE_URL` | `sqlite:///bank.db` | SQLAlchemy URL бази |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `API_KEY` | — (secret) | ключ для admin-операцій (`X-API-Key`), без нього вони вимкнені |
| `HOST`, `PORT` | `127.0.0.1`, `8000` | адреса сервера |

Некоректні значення (наприклад `APP_ENV=staging`) зупиняють запуск з помилкою валідації.
У `production` схема БД створюється тільки міграціями.

## Running locally

```
bank-account-service migrate           # alembic upgrade head
bank-account-service serve             # http://127.0.0.1:8000
uvicorn bank_account_service.api:app --reload   # режим розробки
```

## Running with Docker

```
docker build -t bank-account-service:1.0.0 .
docker run --rm -p 8000:8000 -e LOG_LEVEL=INFO -e API_KEY=<secret> \
    -v bank_data:/app/data bank-account-service:1.0.0
docker compose up --build              # те саме через docker-compose.yml
```

Контейнер при старті застосовує міграції (`serve --migrate`), працює від користувача
`appuser`, зберігає SQLite у volume `/app/data`, а Docker HEALTHCHECK опитує `/health`.

## API

Документація: `/docs` (Swagger UI), `/redoc`, `/openapi.json`.

| Method | Path | Опис |
|---|---|---|
| GET | `/health` | стан сервісу і БД |
| POST | `/clients` | створити клієнта |
| GET | `/clients/{id}`, `/clients/{id}/accounts` | клієнт і його рахунки |
| POST | `/accounts` | відкрити рахунок |
| GET | `/accounts?client_id&number&min_balance&account_type&sort_by_balance&limit&offset` | пошук |
| GET / PATCH | `/accounts/{id}` | рахунок, зміна типу |
| DELETE | `/accounts/{id}` | закрити рахунок (потрібен `X-API-Key`) |
| GET | `/accounts/{id}/transactions` | історія операцій |
| POST | `/accounts/{id}/deposit`, `/accounts/{id}/withdraw` | поповнення, списання |
| POST | `/transfers` | атомарний переказ |
| GET | `/stats`, `/reports/interest-forecast` | статистика, прогноз |
| POST | `/accounts/overview` | паралельний огляд рахунків |

## Testing

```
ruff check .
ruff format --check .
mypy src
pytest -v --cov
```

## Project structure

```
src/bank_account_service/   api, schemas, services, repositories, models, database,
                            config, logging_config, analytics, external_api, migrate, main,
                            migrations/ (Alembic)
tests/                      persistence, API, client, config/health tests
.github/workflows/ci.yml    CI pipeline
Dockerfile, .dockerignore, docker-compose.yml, .env.example, pyproject.toml
```

## CI/CD

`.github/workflows/ci.yml` запускається на push у `main`, на теги `v*` і на pull request:

1. `quality` (matrix Python 3.12, 3.13): ruff check, ruff format --check, mypy, pytest + coverage;
2. `build`: wheel + sdist, встановлення wheel у чисте середовище, upload artifact;
3. `docker`: docker build, запуск контейнера, перевірка `/health`.

Secrets для CI додаються у Settings → Secrets and variables → Actions (`API_KEY`) і
використовуються як `${{ secrets.API_KEY }}`.

## Demo scenario

1. `pytest -v`, `ruff check .`, `mypy src`
2. `python -m build` → `dist/*.whl`, `dist/*.tar.gz`
3. `docker build ...`, `docker run ...`
4. `/health`, `/docs`: створити клієнта, рахунок, поповнення, переказ, перевірити історію
5. показати `.env.example`, `.gitignore` і що `.env` не потрапив у Git

## Authors

Дораж Михайло, група ФеП-31.

## License

MIT
