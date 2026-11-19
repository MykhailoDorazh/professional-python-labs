# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com/), версії — [SemVer](https://semver.org/).

## [1.0.0] — 2026-11-20

### Added
- конфігурація через environment variables і `.env` (`config.py`, pydantic-settings);
- `API_KEY` (secret) для admin-операції закриття рахунку, заголовок `X-API-Key`;
- `/health` з перевіркою БД, structured logging, access log middleware;
- `/reports/interest-forecast` — прогноз коштів (NumPy-реалізація з ЛР №9);
- CLI `bank-account-service serve|migrate|version`, міграції всередині пакета;
- multi-stage Dockerfile, non-root user, HEALTHCHECK, docker-compose, `.dockerignore`;
- GitHub Actions: lint, format, mypy, tests + coverage, build, docker smoke test;
- README, LICENSE, `.env.example`.

### Changed
- URL бази більше не читається при імпорті модуля, а передається через `Settings`.

## [0.9.0] — ЛР №9
- профілювання, NumPy, ThreadPool/ProcessPool, кешування.

## [0.8.0] — ЛР №8
- REST API на FastAPI, асинхронний HTTP-клієнт.

## [0.7.0] — ЛР №7
- SQLite, SQLAlchemy, repositories, транзакції, Alembic.
