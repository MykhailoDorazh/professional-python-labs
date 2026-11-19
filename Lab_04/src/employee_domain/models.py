"""Domain entities: Employee and its subclasses, Department, PayrollRecord."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import ClassVar, Literal

from employee_domain.exceptions import InvalidEmployeeError, InvalidSalaryError
from employee_domain.value_objects import EmployeeId, Money

MIN_SALARY = 0.0
MAX_SALARY = 1_000_000.0
Level = Literal["junior", "middle", "senior"]
LEVEL_BONUS: dict[Level, float] = {"junior": 0.05, "middle": 0.10, "senior": 0.15}


def validate_salary(salary: Money) -> Money:
    if not MIN_SALARY <= salary.amount <= MAX_SALARY:
        raise InvalidSalaryError(salary.amount, MIN_SALARY, MAX_SALARY)
    return salary


@dataclass(frozen=True, slots=True)
class PayrollRecord:
    """Immutable payroll line of one employee for one period."""

    id: int
    employee_id: str
    period: str
    base: Money
    bonus: Money

    @property
    def total(self) -> Money:
        return self.base + self.bonus

    def __str__(self) -> str:
        return (f"#{self.id} {self.period} {self.employee_id}: оклад {self.base} + "
                f"премія {self.bonus} = {self.total}")


class Employee:
    """Employee. Salary is encapsulated: it changes only through
    change_salary()/raise_salary(), which validate the new value."""

    role: ClassVar[str] = "employee"

    def __init__(self, employee_id: str, name: str, position: str, salary: Money) -> None:
        self._id = EmployeeId(employee_id)
        self.name = name
        self.position = position
        self._salary = validate_salary(salary)
        self.department: str | None = None  # код відділу; призначає HRService

    # ---------- properties ----------
    @property
    def employee_id(self) -> str:
        return self._id.value

    @property
    def key(self) -> str:
        """Key for the generic repository."""
        return self._id.value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        value = " ".join(value.split())
        if not value:
            raise InvalidEmployeeError("ПІБ не може бути порожнім")
        self._name = value

    @property
    def position(self) -> str:
        return self._position

    @position.setter
    def position(self, value: str) -> None:
        if not value.strip():
            raise InvalidEmployeeError("Посада не може бути порожньою")
        self._position = value.strip()

    @property
    def salary(self) -> Money:
        return self._salary

    # ---------- behavior ----------
    def change_salary(self, new_salary: Money) -> Money:
        """Set a new salary and return the old one."""
        old, self._salary = self._salary, validate_salary(new_salary)
        return old

    def raise_salary(self, percent: float) -> Money:
        if percent <= 0:
            raise InvalidSalaryError(percent, 0, 100)
        self.change_salary(self._salary * (1 + percent / 100))
        return self._salary

    def bonus(self) -> Money:
        """Monthly bonus; overridden in subclasses (polymorphism)."""
        return Money.zero(self._salary.currency)

    def payroll(self, record_id: int, period: str) -> PayrollRecord:
        return PayrollRecord(record_id, self.employee_id, period, self._salary, self.bonus())

    # ---------- dunder methods ----------
    def __repr__(self) -> str:
        return (f"{type(self).__name__}(employee_id={self.employee_id!r}, name={self.name!r}, "
                f"position={self.position!r}, salary={self._salary.amount!r})")

    def __str__(self) -> str:
        return (f"{self.employee_id} [{self.role}] {self.name}, {self.position}, "
                f"{self.department or '-'}: {self._salary}")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Employee) and self.employee_id == other.employee_id

    def __hash__(self) -> int:
        return hash(self.employee_id)

    def __lt__(self, other: "Employee") -> bool:
        return self._salary < other._salary


class Manager(Employee):
    """Manager: bonus is a percentage of the salary, has a team."""

    role = "manager"

    def __init__(self, employee_id: str, name: str, position: str, salary: Money,
                 *, bonus_rate: float = 0.2) -> None:
        super().__init__(employee_id, name, position, salary)
        if not 0 <= bonus_rate <= 0.5:
            raise InvalidSalaryError(bonus_rate, 0, 0.5)
        self.bonus_rate = bonus_rate
        self.team: list[Employee] = []  # composition/aggregation: менеджер "має" команду

    def add_to_team(self, employee: Employee) -> None:
        if employee is not self and employee not in self.team:
            self.team.append(employee)

    def bonus(self) -> Money:
        # +500 грн за кожного члена команди
        return self.salary * self.bonus_rate + Money(500 * len(self.team), self.salary.currency)


class Developer(Employee):
    """Developer: bonus depends on the level."""

    role = "developer"

    def __init__(self, employee_id: str, name: str, position: str, salary: Money,
                 *, level: Level = "middle", stack: tuple[str, ...] = ()) -> None:
        super().__init__(employee_id, name, position, salary)
        self.level: Level = level
        self.stack = stack

    def bonus(self) -> Money:
        return self.salary * LEVEL_BONUS[self.level]


@dataclass(slots=True)
class Department:
    """Department: aggregates its employees (custom collection)."""

    code: str
    name: str
    _employees: dict[str, Employee] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.code = self.code.strip().upper()
        if not self.code or not self.name.strip():
            raise InvalidEmployeeError("Код і назва відділу обов'язкові")

    @property
    def key(self) -> str:
        return self.code

    def add(self, employee: Employee) -> None:
        self._employees[employee.employee_id] = employee
        employee.department = self.code

    def remove(self, employee: Employee) -> None:
        self._employees.pop(employee.employee_id, None)
        employee.department = None

    def payroll(self) -> Money:
        return sum((e.salary for e in self), start=Money.zero())

    def __len__(self) -> int:
        return len(self._employees)

    def __iter__(self) -> Iterator[Employee]:
        return iter(self._employees.values())

    def __contains__(self, item: object) -> bool:
        return isinstance(item, Employee) and item.employee_id in self._employees

    def __str__(self) -> str:
        return f"{self.code} «{self.name}»: {len(self)} працівн."
