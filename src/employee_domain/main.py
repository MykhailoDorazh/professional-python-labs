"""Demo scenario of the typed employee domain model."""

from collections.abc import Callable

from employee_domain.dto import EmployeePayload, employee_from_payload, employee_to_payload
from employee_domain.exceptions import EmployeeError
from employee_domain.models import Department, Developer, Employee, Manager
from employee_domain.protocols import HasKey
from employee_domain.repositories import InMemoryRepository
from employee_domain.services import (
    ConsoleNotifier,
    HRService,
    JsonReport,
    PayrollService,
    TextReport,
    clamp,
)
from employee_domain.value_objects import Money

DEPARTMENTS = (("IT", "Інформаційні технології"), ("FIN", "Фінанси"), ("HR", "Персонал"))


def build_application() -> tuple[HRService, PayrollService, InMemoryRepository[Employee]]:
    """Manual dependency-injection container: all wiring is in one place."""
    employees = InMemoryRepository[Employee]()
    departments = InMemoryRepository[Department]()
    for code, name in DEPARTMENTS:
        departments.add(Department(code, name))
    hr = HRService(employees=employees, departments=departments, notifier=ConsoleNotifier())
    payroll = PayrollService(employees=employees)
    return hr, payroll, employees


def main() -> None:
    hr, payroll, repository = build_application()

    print("1. Додавання працівників і призначення відділу:")
    lead = Manager("E0001", "Олена Коваль", "Керівник розробки", Money(95_000), bonus_rate=0.15)
    hr.add_employee(lead, "IT")
    hr.add_employee(Developer("E0002", "Іван Петренко", "Python-розробник", Money(72_000),
                              level="senior", stack=("Python", "FastAPI")), "IT")
    hr.add_employee(Developer("E0003", "Тарас Новак", "Розробник", Money(41_500), level="junior"),
                    "IT")
    hr.add_employee(Employee("E0004", "Андрій  Мельник", "Бухгалтер", Money(36_800)), "FIN")
    payload: EmployeePayload = {"employee_id": "e0005", "name": "Марія Бондар",
                                "position": "HR-менеджер", "role": "manager", "department": "HR",
                                "salary": 48_000, "currency": "UAH", "bonus_rate": 0.1}
    hr.add_employee(employee_from_payload(payload), payload["department"])
    for member in hr.find_by_department("IT")[1:]:
        lead.add_to_team(member)

    print("\n2. Помилки валідації:")
    attempts: tuple[Callable[[], object], ...] = (
        lambda: Employee("E12", "Олег", "Аналітик", Money(30_000)),
        lambda: Employee("E0006", "   ", "Аналітик", Money(30_000)),
        lambda: Employee("E0006", "Олег Шевченко", "Аналітик", Money(2_000_000)),
        lambda: hr.add_employee(Employee("E0006", "Олег Шевченко", "Аналітик", Money(30_000)),
                                "SALES"),
        lambda: hr.add_employee(Employee("E0002", "Дублікат", "Тестувальник", Money(1)), "IT"),
        lambda: hr.find_employee("E9999"),
    )
    for attempt in attempts:
        try:
            attempt()
        except EmployeeError as error:
            print(f"    {type(error).__name__}: {error}")
    try:
        Money(-5)
    except ValueError as error:
        print(f"    Money(-5) -> ValueError: {error}")

    print("\n3. Пошук, зміна окладу, переведення:")
    print("   відділ IT:", [e.employee_id for e in hr.find_by_department("it")])
    print("   пошук 'розроб':", [e.name for e in hr.search("розроб")])
    hr.change_salary("E0003", Money(45_000))
    hr.transfer("E0004", "HR")
    print("  ", hr.find_employee("E0004"))

    print("\n4. Dunder methods і колекції:")
    employee = hr.find_employee("E0002")
    print("   repr:", repr(employee))
    print("   str: ", employee)
    print("   len(repository) =", len(repository), "| 'e0005' in repository:", "e0005" in repository)
    print("   E0002 > E0003 (за окладом):", hr.find_employee("E0003") < employee)
    print("   Money(100) + Money(50.5) =", Money(100) + Money(50.5),
          "| Money(90) / 3 =", Money(90) / 3)

    print("\n5. Нарахування за місяць (поліморфізм bonus()):")
    for record in payroll.run_payroll("2026-11"):
        print("  ", record)

    print("\n6. Статистика:")
    print("   фонд оплати праці:", payroll.total_payroll())
    print("   середня зарплата:", payroll.average_salary())
    print("   середня в IT:", payroll.average_salary(hr.find_by_department("IT")))
    top = payroll.highest_paid()
    print("   максимальна зарплата:", top.name if top else "-", top.salary if top else "")
    print("   рейтинг:", [e.employee_id for e in payroll.ranking()])

    print("\n7. Звіти (ABC ReportFormatter, Template Method):")
    summary = payroll.summary()
    print(TextReport().render(summary))
    print(JsonReport().render(summary))

    print("\n8. Типи:")
    print("   isinstance(employee, HasKey) [runtime_checkable]:", isinstance(employee, HasKey))
    print("   clamp(15, 0, 10) =", clamp(15, 0, 10), "| clamp(0.7, 0.0, 0.5) =", clamp(0.7, 0.0, 0.5))
    print("   payload:", employee_to_payload(repository["E0005"]))


if __name__ == "__main__":
    main()
