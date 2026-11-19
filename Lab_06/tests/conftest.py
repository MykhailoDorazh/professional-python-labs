"""Shared fixtures (pytest finds them automatically, no import needed)."""

from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import Mock, create_autospec

import pytest

from bank_app.config import AppConfig
from bank_app.models import Account, CurrentAccount, Customer, SavingsAccount
from bank_app.protocols import Notifier
from bank_app.repositories import InMemoryRepository
from bank_app.services import BankService
from bank_app.value_objects import Money


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Autouse: tests never depend on the developer's BANK_CURRENCY variable."""
    monkeypatch.delenv("BANK_CURRENCY", raising=False)


@pytest.fixture
def owner() -> Customer:
    return Customer(1, "Іван Петренко", "ivan@example.com")


@pytest.fixture
def account_factory(owner: Customer) -> Callable[..., Account]:
    """Fixture factory: creates accounts with the needed parameters."""

    def create(number: str = "UA100001", balance: float = 1000.0,
               kind: str = "current", **kwargs: object) -> Account:
        if kind == "savings":
            return SavingsAccount(number, owner, Money(balance), **kwargs)  # type: ignore[arg-type]
        return CurrentAccount(number, owner, Money(balance), **kwargs)  # type: ignore[arg-type]

    return create


@pytest.fixture
def current_account(account_factory: Callable[..., Account]) -> Account:
    return account_factory("UA100001", 1000.0)


@pytest.fixture(params=[CurrentAccount, SavingsAccount], ids=["current", "savings"])
def any_account(request: pytest.FixtureRequest, owner: Customer) -> Account:
    """Parameterized fixture: every test using it runs for both account types."""
    account_class: type[Account] = request.param
    return account_class("UA100005", owner, Money(500))


@pytest.fixture
def repository() -> InMemoryRepository[Account]:
    return InMemoryRepository()


@pytest.fixture
def notifier() -> Mock:
    """Autospec mock: calling a method that Notifier does not have fails."""
    return create_autospec(Notifier, instance=True)


@pytest.fixture
def bank(repository: InMemoryRepository[Account], notifier: Mock,
         current_account: Account) -> BankService:
    service = BankService(repository, notifier)
    service.open_account(current_account)
    notifier.reset_mock()  # повідомлення про відкриття рахунку не заважає тестам
    return service


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(("deposit", "withdraw"), "UAH", 100_000.0, True)


@pytest.fixture
def write_file(tmp_path: Path) -> Callable[[str, str], Path]:
    """Creates a UTF-8 file inside the isolated temporary directory."""

    def write(name: str, text: str) -> Path:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    return write


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Yield fixture: working directory = temporary copy of the project data."""
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "data").mkdir()
    for name in ("accounts.csv", "operations.csv"):
        (tmp_path / "data" / name).write_bytes((root / "data" / name).read_bytes())
    (tmp_path / "config.yaml").write_bytes((root / "config.yaml").read_bytes())
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    # teardown: перевіряємо, що тест не залишив тимчасових .tmp файлів
    assert not list(tmp_path.rglob("*.tmp"))
