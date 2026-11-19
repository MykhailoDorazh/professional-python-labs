"""Application entry point: demo scenario and menu-driven interface."""

import sys

from employee_manager.config import CURRENCY
from employee_manager.console import (
    ask,
    ask_float,
    money,
    print_departments,
    print_employees,
    print_statistics,
)
from employee_manager.exceptions import EmployeeError
from employee_manager.models import Employee
from employee_manager.services import (
    add_employee,
    average_salary,
    calculate_statistics,
    change_position,
    change_salary,
    department_summary,
    find_by_department,
    find_employee,
    highest_paid,
    search_employees,
    sort_employees,
    total_payroll,
    transfer,
)


def create_demo_employees() -> list[Employee]:
    """Initial data set."""
    return [
        Employee("E1001", "Іван Петренко", "Розробник", "IT", 52_000),
        Employee("E1002", "Олена Коваль", "Тімлід", "IT", 78_500),
        Employee("E1003", "Андрій Мельник", "Бухгалтер", "Фінанси", 31_200),
        Employee("E1004", "Марія Бондар", "HR-менеджер", "HR", 29_800),
        Employee("E1005", "Олег Шевченко", "Аналітик", "Фінанси", 41_750.50),
    ]


def run_demo(employees: list[Employee]) -> None:
    """Non-interactive scenario that shows all features."""
    print_employees(employees, "Список працівників")
    print_employees(find_by_department(employees, "it"), "Пошук за відділом «IT»")

    employee = find_employee(employees, "e1003")
    print(f"\nПошук E1003: {employee.name}, {employee.position}, {employee.formatted_salary}")
    print(f"Зміна зарплати E1003 на 33 500: {money(change_salary(employee, 33_500))} {CURRENCY}")
    change_position(employee, "Головний бухгалтер")
    transfer(find_employee(employees, "E1004"), "Адміністрація")
    print("E1003 -> посада «Головний бухгалтер»; E1004 переведено до відділу «Адміністрація»")

    attempts = [
        ("зарплата -100", lambda: change_salary(employee, -100)),
        ("пошук E9999", lambda: find_employee(employees, "E9999")),
        ("дубль E1001", lambda: add_employee(
            employees, Employee("E1001", "Тест", "Тест", "IT", 1))),
    ]
    for title, action in attempts:
        try:
            action()
        except EmployeeError as error:
            print(f"Відхилено ({title}): {error}")

    print(f"\nСередня зарплата:     {money(average_salary(employees))} {CURRENCY}")
    top = highest_paid(employees)
    if top is not None:
        print(f"Максимальна зарплата: {top.name} — {top.formatted_salary}")
    print(f"Фонд оплати праці:    {money(total_payroll(employees))} {CURRENCY}")

    found = search_employees(employees, name_part="о", min_salary=40_000)
    print_employees(found, "Пошук: ПІБ містить «о» і зарплата >= 40 000")
    print_employees(sort_employees(employees), "Сортування за зарплатою (спадання)")
    print_statistics(calculate_statistics(employees))
    print_departments(department_summary(employees))


def print_menu() -> None:
    print()
    print("===== Облік працівників =====")
    print("1. Список працівників")
    print("2. Пошук за відділом")
    print("3. Додати працівника")
    print("4. Змінити зарплату")
    print("5. Перевести до іншого відділу")
    print("6. Пошук за ПІБ і зарплатою")
    print("7. Статистика і фонд оплати праці")
    print("9. Показати меню")
    print("0. Вихід")


def handle_command(command: str, employees: list[Employee]) -> bool:
    """Execute one menu command. Returns False when the user exits."""
    if command == "1":
        print_employees(sort_employees(employees, by="id", descending=False))
    elif command == "2":
        department = ask("Відділ: ")
        print_employees(find_by_department(employees, department), f"Відділ «{department}»")
    elif command == "3":
        employee = add_employee(employees, Employee(
            ask("Табельний номер (E + 4 цифри): "), ask("ПІБ: "), ask("Посада: "),
            ask("Відділ: "), ask_float("Зарплата: ")))
        print(f"  Додано {employee.employee_id}")
    elif command == "4":
        employee = find_employee(employees, ask("Табельний номер: "))
        salary = change_salary(employee, ask_float("Нова зарплата: "))
        print(f"  Успішно. {employee.name}: {money(salary)} {CURRENCY}")
    elif command == "5":
        employee = find_employee(employees, ask("Табельний номер: "))
        transfer(employee, ask("Новий відділ: "))
        print(f"  {employee.name} тепер у відділі «{employee.department}»")
    elif command == "6":
        name = ask("Частина ПІБ (Enter - усі): ")
        minimum = ask_float("Мінімальна зарплата: ")
        print_employees(search_employees(employees, name, min_salary=minimum),
                        "Результат пошуку")
    elif command == "7":
        print_statistics(calculate_statistics(employees))
        print_departments(department_summary(employees))
    elif command == "9":
        print_menu()
    elif command == "0":
        print("До побачення!")
        return False
    else:
        print("  Невідома команда (9 - показати меню)")
    return True


def run_menu(employees: list[Employee]) -> None:
    """Menu-driven interface with keyboard input."""
    print_menu()
    running = True
    while running:
        print()
        try:
            running = handle_command(ask("Оберіть команду: "), employees)
        except EmployeeError as error:
            print(f"  Помилка: {error}")
        except EOFError:
            break


def main() -> None:
    employees = create_demo_employees()
    if "--menu" in sys.argv[1:]:
        run_menu(employees)
    else:
        run_demo(employees)


if __name__ == "__main__":
    main()
