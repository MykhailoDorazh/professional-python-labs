"""Shared fixtures (pytest finds them automatically, no import needed)."""

from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import Mock, create_autospec

import pytest

from employee_app.config import AppConfig
from employee_app.models import Department, Developer, Employee, Manager
from employee_app.protocols import Notifier
from employee_app.repositories import InMemoryRepository
from employee_app.services import HRService, PayrollService
from employee_app.value_objects import Money

DEPARTMENTS = {"IT": "Інформаційні технології", "FIN": "Фінанси", "HR": "Персонал"}


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Autouse: tests never depend on the developer's EMPLOYEE_MIN_SALARY variable."""
    monkeypatch.delenv("EMPLOYEE_MIN_SALARY", raising=False)


@pytest.fixture
def employee_factory() -> Callable[..., Employee]:
    """Fixture factory: creates employees of any role with the needed parameters."""

    def create(employee_id: str = "E0001", salary: float = 50_000.0, role: str = "employee",
               name: str = "Іван Петренко", position: str = "Розробник",
               **kwargs: object) -> Employee:
        classes: dict[str, type[Employee]] = {"employee": Employee, "manager": Manager,
                                              "developer": Developer}
        return classes[role](employee_id, name, position, Money(salary), **kwargs)

    return create


@pytest.fixture
def employee(employee_factory: Callable[..., Employee]) -> Employee:
    return employee_factory("E0001", 50_000.0)


@pytest.fixture(params=[Employee, Manager, Developer], ids=["employee", "manager", "developer"])
def any_employee(request: pytest.FixtureRequest) -> Employee:
    """Parameterized fixture: every test using it runs for all three roles."""
    employee_class: type[Employee] = request.param
    return employee_class("E0005", "Марія Бондар", "Спеціаліст", Money(40_000))


@pytest.fixture
def employees() -> InMemoryRepository[Employee]:
    return InMemoryRepository()


@pytest.fixture
def departments() -> InMemoryRepository[Department]:
    repository: InMemoryRepository[Department] = InMemoryRepository()
    for code, name in DEPARTMENTS.items():
        repository.add(Department(code, name))
    return repository


@pytest.fixture
def notifier() -> Mock:
    """Autospec mock: calling a method that Notifier does not have fails."""
    return create_autospec(Notifier, instance=True)


@pytest.fixture
def hr(employees: InMemoryRepository[Employee], departments: InMemoryRepository[Department],
       notifier: Mock, employee: Employee) -> HRService:
    service = HRService(employees, departments, notifier)
    service.add_employee(employee, "IT")
    notifier.reset_mock()  # повідомлення про зарахування не заважає тестам
    return service


@pytest.fixture
def staffed(hr: HRService, employee_factory: Callable[..., Employee]) -> HRService:
    """IT: 50 000 + 90 000 (manager), FIN: 30 000.50; HR is empty."""
    hr.add_employee(employee_factory("E0002", 90_000, "manager", name="Олена Коваль"), "IT")
    hr.add_employee(employee_factory("E0003", 30_000.5, name="Андрій Мельник"), "FIN")
    return hr


@pytest.fixture
def payroll(employees: InMemoryRepository[Employee]) -> PayrollService:
    return PayrollService(employees)


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(dict(DEPARTMENTS), 8_000.0, 1_000_000.0, "UAH", True)


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
    (tmp_path / "data" / "employees.csv").write_bytes((root / "data/employees.csv").read_bytes())
    (tmp_path / "config.yaml").write_bytes((root / "config.yaml").read_bytes())
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    # teardown: перевіряємо, що тест не залишив тимчасових .tmp файлів
    assert not list(tmp_path.rglob("*.tmp"))
