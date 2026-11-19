"""Console input/output helpers: tables, validated keyboard input."""

import sys

from employee_manager.config import CURRENCY
from employee_manager.models import Employee


def ask(prompt: str) -> str:
    """Read a line from the keyboard.

    When the input is redirected from a file (not a terminal), the entered
    value is echoed, so the session log looks the same as an interactive one.
    """
    value = input(prompt)
    if not sys.stdin.isatty():
        print(value)
    return value.strip()


def ask_float(prompt: str) -> float:
    """Ask for a number until a valid one is entered."""
    while True:
        text = ask(prompt).replace(",", ".").replace(" ", "")
        try:
            return float(text)
        except ValueError:
            print("  Помилка: введіть число, наприклад 25000")


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def print_employees(employees: list[Employee], title: str = "Працівники") -> None:
    """Print employees as a table."""
    print(f"\n{title}:")
    if not employees:
        print("  (немає працівників)")
        return
    print(f"  {'ID':<7}{'ПІБ':<20}{'Посада':<20}{'Відділ':<15}{'Зарплата, ' + CURRENCY:>16}")
    print("  " + "-" * 78)
    for e in employees:
        print(f"  {e.employee_id:<7}{e.name:<20}{e.position:<20}{e.department:<15}"
              f"{money(e.salary):>16}")


def print_statistics(stats: dict[str, float]) -> None:
    """Print salary statistics."""
    print("\nСтатистика зарплат:")
    print(f"  кількість працівників: {stats['count']:.0f}")
    print(f"  фонд оплати праці:     {money(stats['payroll'])} {CURRENCY}")
    print(f"  середня зарплата:      {money(stats['average'])} {CURRENCY}")
    print(f"  мінімальна:            {money(stats['minimum'])} {CURRENCY}")
    print(f"  максимальна:           {money(stats['maximum'])} {CURRENCY}")


def print_departments(summary: dict[str, tuple[int, float]]) -> None:
    print("\nВідділи:")
    for department, (count, payroll) in summary.items():
        print(f"  {department:<15} працівників: {count}  фонд: {money(payroll)} {CURRENCY}")
