"""Experiment: service creates its dependency itself (A) vs dependency injection (B)."""

from employee_domain.models import Employee
from employee_domain.protocols import Notifier
from employee_domain.services import ConsoleNotifier, InMemoryNotifier
from employee_domain.value_objects import Money


class SalaryServiceA:
    """Variant A: concrete dependency is hard-coded."""

    def __init__(self) -> None:
        self.notifier = ConsoleNotifier()

    def raise_salary(self, employee: Employee, percent: float) -> None:
        employee.raise_salary(percent)
        self.notifier.send(employee.employee_id, f"Оклад підвищено на {percent} %")


class SalaryServiceB:
    """Variant B: dependency is injected and typed by the Notifier protocol."""

    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier

    def raise_salary(self, employee: Employee, percent: float) -> None:
        employee.raise_salary(percent)
        self.notifier.send(employee.employee_id, f"Оклад підвищено на {percent} %")


def main() -> None:
    print("Варіант A (жорстка залежність) - повідомлення лише друкуються, перевірити їх у тесті ніяк:")
    SalaryServiceA().raise_salary(Employee("E0001", "Іван Петренко", "Розробник", Money(50_000)), 10)

    print("\nВаріант B (DI) - у тесті підставляємо InMemoryNotifier і перевіряємо результат:")
    fake = InMemoryNotifier()
    employee = Employee("E0002", "Олена Коваль", "Аналітик", Money(40_000))
    SalaryServiceB(fake).raise_salary(employee, 5)
    print("    отримані повідомлення:", fake.messages, "| новий оклад:", employee.salary)
    assert fake.messages == [("E0002", "Оклад підвищено на 5 %")]
    assert employee.salary == Money(42_000)
    print("    перевірка пройдена; у production передаємо ConsoleNotifier або EmailNotifier")
    SalaryServiceB(ConsoleNotifier()).raise_salary(employee, 5)


if __name__ == "__main__":
    main()
