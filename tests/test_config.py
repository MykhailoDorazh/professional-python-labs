"""Configuration from environment variables, secrets, health and admin endpoints."""

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from bank_account_service.analytics import project_balance, project_balances
from bank_account_service.api import create_app
from bank_account_service.config import Settings, get_settings
from bank_account_service.main import main


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """No real .env and no inherited variables: every test sets what it needs."""
    for name in ("APP_ENV", "DATABASE_URL", "LOG_LEVEL", "API_KEY", "PORT", "APP_NAME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_default_settings() -> None:
    settings = Settings()
    assert settings.app_env == "development"
    assert settings.database_url == "sqlite:///bank.db"
    assert settings.log_level == "INFO"
    assert settings.api_key is None
    assert not settings.is_production


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////app/data/bank.db")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PORT", "9000")
    settings = get_settings()
    assert (settings.app_env, settings.database_url, settings.log_level, settings.port) == (
        "production",
        "sqlite:////app/data/bank.db",
        "DEBUG",
        9000,
    )
    assert settings.is_production


def test_dotenv_file_is_read(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("APP_ENV=test\nLOG_LEVEL=WARNING\n", encoding="utf-8")
    settings = Settings()
    assert (settings.app_env, settings.log_level) == ("test", "WARNING")


@pytest.mark.parametrize(
    "name, value", [("APP_ENV", "staging"), ("LOG_LEVEL", "LOUD"), ("PORT", "70000")]
)
def test_invalid_configuration_fails_fast(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings()


def test_secret_is_not_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "super-secret-value")
    settings = Settings()
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "super-secret-value"
    assert "super-secret-value" not in repr(settings)
    assert "super-secret-value" not in str(settings.model_dump())


def make_client(tmp_path: Path, **overrides: object) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'cfg.db'}", app_env="test", **overrides
    )  # type: ignore[arg-type]
    return TestClient(create_app(settings))


def test_health_reports_environment_and_database(tmp_path: Path) -> None:
    with make_client(tmp_path, app_env="production") as client:
        body = client.get("/health").json()
    assert body == {
        "status": "ok",
        "version": "1.0.0",
        "environment": "production",
        "database": "ok",
    }


def test_health_is_503_when_database_is_down(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        client.app.state.engine.dispose()  # type: ignore[attr-defined]
        client.app.state.engine = None  # type: ignore[attr-defined]
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


@pytest.mark.parametrize(
    "api_key, header, status",
    [
        (None, None, 403),  # admin API disabled without API_KEY
        ("s3cret-test", None, 401),  # header missing
        ("s3cret-test", "wrong", 401),  # wrong key
        ("s3cret-test", "s3cret-test", 404),  # authorized -> account 99 does not exist
    ],
)
def test_admin_endpoint_requires_api_key(
    tmp_path: Path, api_key: str | None, header: str | None, status: int
) -> None:
    headers = {"X-API-Key": header} if header else {}
    with make_client(tmp_path, api_key=api_key) as client:
        assert client.delete("/accounts/99", headers=headers).status_code == status


def test_interest_forecast(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        client.post("/clients", json={"full_name": "Анна Коваль"})
        client.post(
            "/accounts",
            json={
                "client_id": 1,
                "number": "UA00000001",
                "initial_deposit": "1000",
                "account_type": "savings",
            },
        )
        body = client.get("/reports/interest-forecast").json()
    assert body["accounts"] == 1
    assert body["total_now"] == "1000.00"
    assert body["total_in_one_year"] == "1127.47"  # 12 % with daily capitalisation


def test_vectorized_forecast_equals_reference() -> None:
    balances, rates = [0, 1, 15_208, 100_000, 7_654_321], [1200, 50, 1200, 1200, 50]
    expected = [project_balance(b, r) for b, r in zip(balances, rates, strict=True)]
    assert project_balances(np.array(balances), np.array(rates)).tolist() == expected


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    main(["version"])
    assert capsys.readouterr().out.strip() == "bank-account-service 1.0.0"


def test_cli_migrate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    main(["migrate"])
    assert (tmp_path / "cli.db").exists()
