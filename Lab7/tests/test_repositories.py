"""Integration tests: Repository + SQLAlchemy + SQLite (CRUD)."""

import pytest
from sqlalchemy.orm import Session

from bank_db.database import transaction
from bank_db.models import Account, Client, Transaction
from bank_db.repositories import AccountRepository, ClientRepository, TransactionRepository


def test_create_and_read_client(session: Session) -> None:
    repo = ClientRepository(session)
    with transaction(session):
        client = repo.add(Client(full_name="Анна Коваль", email="anna@example.com"))
    assert client.id is not None
    session.expire_all()  # force a real SELECT instead of the identity map
    loaded = repo.get_by_id(client.id)
    assert loaded is not None
    assert loaded.full_name == "Анна Коваль"
    assert repo.count() == 1


def test_update_client(session: Session) -> None:
    repo = ClientRepository(session)
    with transaction(session):
        client = repo.add(Client(full_name="Олег"))
    with transaction(session):
        client.full_name = "Олег Мельник"
    session.expire_all()
    assert repo.get_by_id(client.id).full_name == "Олег Мельник"  # type: ignore[union-attr]


def test_delete_client_cascades_to_accounts(session: Session) -> None:
    clients, accounts = ClientRepository(session), AccountRepository(session)
    with transaction(session):
        client = clients.add(Client(full_name="Ірина"))
        accounts.add(Account(number="UA1", client_id=client.id))
    with transaction(session):
        clients.delete(client)
    assert clients.get_by_id(client.id) is None
    assert accounts.get_by_number("UA1") is None


def test_find_client_by_name_fragment(session: Session) -> None:
    repo = ClientRepository(session)
    with transaction(session):
        for name in ("Анна Коваль", "Олег Мельник", "Ірина Коваленко"):
            repo.add(Client(full_name=name))
    assert [c.full_name for c in repo.find_by_name("Ковал")] == ["Анна Коваль", "Ірина Коваленко"]


def test_account_crud(session: Session) -> None:
    clients, accounts = ClientRepository(session), AccountRepository(session)
    with transaction(session):
        client = clients.add(Client(full_name="Анна"))
        account = accounts.add(Account(number="UA1", client_id=client.id, balance_cents=100))
    assert accounts.get_by_number("UA1") is account                     # Read
    with transaction(session):
        account.balance_cents = 250                                     # Update
    session.expire_all()
    assert accounts.get_by_id(account.id).balance_cents == 250  # type: ignore[union-attr]
    with transaction(session):
        accounts.delete(account)                                        # Delete
    assert accounts.get_by_number("UA1") is None


def test_relationship_client_accounts(session: Session) -> None:
    clients, accounts = ClientRepository(session), AccountRepository(session)
    with transaction(session):
        client = clients.add(Client(full_name="Анна"))
        accounts.add(Account(number="UA2", client_id=client.id))
        accounts.add(Account(number="UA1", client_id=client.id))
    session.expire_all()
    loaded = clients.get_by_id(client.id)
    assert loaded is not None
    assert [a.number for a in loaded.accounts] == ["UA2", "UA1"]   # order_by Account.id
    assert loaded.accounts[0].client is loaded                      # back_populates


def test_filter_and_pagination(session: Session) -> None:
    clients, accounts = ClientRepository(session), AccountRepository(session)
    with transaction(session):
        client = clients.add(Client(full_name="Анна"))
        for n, cents, kind in (("UA1", 100, "current"), ("UA2", 900, "savings"), ("UA3", 500, "current")):
            accounts.add(Account(number=n, client_id=client.id, balance_cents=cents, account_type=kind))
    rich = accounts.filter(min_balance_cents=500, order_by_balance=True)
    assert [a.number for a in rich] == ["UA2", "UA3"]
    assert [a.number for a in accounts.filter(account_type="current")] == ["UA1", "UA3"]
    assert [a.number for a in accounts.get_all(limit=2, offset=1)] == ["UA2", "UA3"]
    assert accounts.total_balance_cents() == 1500


def test_transactions_history_order(session: Session) -> None:
    clients, accounts, txs = (
        ClientRepository(session), AccountRepository(session), TransactionRepository(session)
    )
    with transaction(session):
        client = clients.add(Client(full_name="Анна"))
        account = accounts.add(Account(number="UA1", client_id=client.id))
        for kind, amount in (("deposit", 500), ("withdraw", 200), ("deposit", 100)):
            txs.add(Transaction(account_id=account.id, kind=kind, amount_cents=amount,
                                balance_after_cents=0))
    history = txs.list_for_account(account.id)
    assert [(t.kind, t.amount_cents) for t in history] == [
        ("deposit", 500), ("withdraw", 200), ("deposit", 100)]
    assert all(t.created_at is not None for t in history)


@pytest.mark.parametrize("limit, expected", [(None, 3), (1, 1), (10, 3)])
def test_get_all_limit(session: Session, limit: int | None, expected: int) -> None:
    repo = ClientRepository(session)
    with transaction(session):
        for name in "ABC":
            repo.add(Client(full_name=name))
    assert len(repo.get_all(limit=limit)) == expected
