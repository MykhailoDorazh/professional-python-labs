"""API integration tests: HTTP request -> FastAPI -> service -> SQLite test DB."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from bank_api.api import create_app
from bank_api.database import init_db, make_engine, make_session_factory


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(f"sqlite:///{tmp_path / 'api.db'}")
    with TestClient(app) as test_client:  # `with` runs the lifespan (engine, tables)
        yield test_client


@pytest.fixture
def seeded(client: TestClient) -> TestClient:
    """Client 1 with UA00000001 (1000.00) and UA00000002 (250.00, savings)."""
    client.post("/clients", json={"full_name": "Анна Коваль", "email": "anna@example.com"})
    client.post("/accounts", json={"client_id": 1, "number": "UA00000001",
                                   "initial_deposit": "1000"})
    client.post("/accounts", json={"client_id": 1, "number": "UA00000002",
                                   "initial_deposit": "250", "account_type": "savings"})
    return client


def test_root_and_health(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok", "version": "0.8.0"}


def test_create_client(client: TestClient) -> None:
    response = client.post("/clients", json={"full_name": "  Олег Мельник "})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "full_name": "Олег Мельник", "email": None}


@pytest.mark.parametrize("payload", [
    {"full_name": "A"},                                  # too short
    {"full_name": "     "},                              # only spaces
    {"full_name": "Анна", "email": "not-an-email"},      # invalid email
    {},                                                  # missing field
])
def test_create_client_validation(client: TestClient, payload: dict[str, str]) -> None:
    assert client.post("/clients", json=payload).status_code == 422


def test_create_account_and_get(seeded: TestClient) -> None:
    response = seeded.get("/accounts/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "number": "UA00000001", "client_id": 1,
                                "account_type": "current", "balance": "1000.00"}
    assert [a["number"] for a in seeded.get("/clients/1/accounts").json()] == [
        "UA00000001", "UA00000002"]


@pytest.mark.parametrize("payload, status", [
    ({"client_id": 1, "number": "UA00000001"}, 409),             # duplicate number
    ({"client_id": 9, "number": "UA00000009"}, 404),             # unknown client
    ({"client_id": 1, "number": "UA1"}, 422),                    # wrong number format
    ({"client_id": 1, "number": "UA00000009", "initial_deposit": "-1"}, 422),
    ({"client_id": 1, "number": "UA00000009", "account_type": "crypto"}, 422),
])
def test_create_account_errors(seeded: TestClient, payload: dict[str, object], status: int) -> None:
    assert seeded.post("/accounts", json=payload).status_code == status


def test_unknown_account_returns_structured_404(client: TestClient) -> None:
    response = client.get("/accounts/404")
    assert response.status_code == 404
    assert response.json() == {"error": "AccountNotFoundError",
                                "detail": "Рахунок id=404 не знайдено"}


def test_deposit_and_withdraw(seeded: TestClient) -> None:
    response = seeded.post("/accounts/1/deposit", json={"amount": "150.50"})
    assert response.status_code == 200
    body = response.json()
    assert body["account"]["balance"] == "1150.50"
    assert body["transaction"]["kind"] == "deposit"
    assert body["transaction"]["amount"] == "150.50"
    response = seeded.post("/accounts/1/withdraw", json={"amount": "1150.50"})
    assert response.json()["account"]["balance"] == "0.00"


def test_withdraw_more_than_balance_is_conflict(seeded: TestClient) -> None:
    response = seeded.post("/accounts/2/withdraw", json={"amount": "250.01"})
    assert response.status_code == 409
    assert response.json()["error"] == "InsufficientFundsError"
    assert seeded.get("/accounts/2").json()["balance"] == "250.00"


@pytest.mark.parametrize("amount", ["0", "-5", "1.001", "abc", None])
def test_invalid_amount_is_422(seeded: TestClient, amount: str | None) -> None:
    assert seeded.post("/accounts/1/deposit", json={"amount": amount}).status_code == 422


def test_transfer_success(seeded: TestClient) -> None:
    response = seeded.post("/transfers", json={"from_account": "UA00000001",
                                               "to_account": "UA00000002", "amount": "400"})
    assert response.status_code == 201
    body = response.json()
    assert body["from_account"]["balance"] == "600.00"
    assert body["to_account"]["balance"] == "650.00"
    history = seeded.get("/accounts/2/transactions", params={"kind": "transfer_in"}).json()
    assert [(t["kind"], t["counterparty"], t["amount"]) for t in history] == [
        ("transfer_in", "UA00000001", "400.00")]


def test_transfer_to_unknown_account_is_rolled_back(seeded: TestClient) -> None:
    response = seeded.post("/transfers", json={"from_account": "UA00000001",
                                               "to_account": "UA00000099", "amount": "400"})
    assert response.status_code == 404
    assert seeded.get("/accounts/1").json()["balance"] == "1000.00"
    assert len(seeded.get("/accounts/1/transactions").json()) == 1


def test_list_accounts_query_parameters(seeded: TestClient) -> None:
    def numbers(**params: object) -> list[str]:
        return [a["number"] for a in seeded.get("/accounts", params=params).json()]

    assert numbers() == ["UA00000001", "UA00000002"]
    assert numbers(min_balance=500) == ["UA00000001"]
    assert numbers(account_type="savings") == ["UA00000002"]
    assert numbers(sort_by_balance=True, limit=1) == ["UA00000001"]
    assert numbers(number="002") == ["UA00000002"]
    assert numbers(offset=1) == ["UA00000002"]
    assert seeded.get("/accounts", params={"limit": 0}).status_code == 422


def test_patch_and_delete_account(seeded: TestClient) -> None:
    response = seeded.patch("/accounts/1", json={"account_type": "savings"})
    assert response.json()["account_type"] == "savings"
    assert seeded.delete("/accounts/1").status_code == 409          # money left
    seeded.post("/accounts/2/withdraw", json={"amount": "250"})
    assert seeded.delete("/accounts/2").status_code == 204
    assert seeded.get("/accounts/2").status_code == 404


def test_stats(seeded: TestClient) -> None:
    seeded.post("/accounts/2/withdraw", json={"amount": "50"})
    assert seeded.get("/stats").json() == {"clients": 1, "accounts": 2,
                                           "total_funds": "1200.00", "turnover": "1300.00"}


def test_accounts_overview_concurrent(seeded: TestClient) -> None:
    response = seeded.post("/accounts/overview", json={"account_ids": [1, 2, 99],
                                                       "history_limit": 1})
    assert response.status_code == 200
    body = response.json()
    assert (body["requested"], body["succeeded"]) == (3, 2)
    assert [item["ok"] for item in body["items"]] == [True, True, False]   # order kept
    assert body["items"][0]["account"]["balance"] == "1000.00"
    assert len(body["items"][1]["last_transactions"]) == 1


def test_openapi_schema_lists_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/clients", "/accounts", "/accounts/{account_id}", "/accounts/{account_id}/deposit",
            "/accounts/{account_id}/withdraw", "/accounts/{account_id}/transactions",
            "/transfers", "/accounts/overview"} <= set(paths)


@pytest.mark.asyncio
async def test_api_through_httpx_async_client(tmp_path: Path) -> None:
    """The same app tested with httpx.AsyncClient + ASGITransport (no network)."""
    url = f"sqlite:///{tmp_path / 'async.db'}"
    app = create_app(url)
    engine = make_engine(url)
    init_db(engine)
    app.state.session_factory = make_session_factory(engine)  # lifespan is not run here
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await ac.post("/clients", json={"full_name": "Ірина Бондар"})
        assert created.status_code == 201
        account = await ac.post("/accounts", json={"client_id": 1, "number": "UA00000007",
                                                   "initial_deposit": "70"})
        assert account.json()["balance"] == "70.00"
    engine.dispose()
