"""Entry point: analysis of employee data."""

from pathlib import Path

from employee_analytics.analytics import (
    average_salary,
    create_employee,
    department_summary,
    export_summary,
    highest_paid,
    salary_range,
    sum_values,
    total_payroll,
)
from employee_analytics.data import DEPARTMENTS, employees
from employee_analytics.decorators import OPERATION_HISTORY
from employee_analytics.processors import (
    count_by_department,
    create_employee_index,
    filter_by_min_salary,
    filter_items,
    find_by_id,
    find_by_name,
    find_employee_linear,
    get_positions,
    get_used_departments,
    group_by_department,
    group_nested,
    make_department_filter,
    pipeline,
    sort_by_salary,
    sort_items,
)


def print_employees(title: str, items: list[dict]) -> None:
    print(f"\n{title}")
    print("-" * 75)
    for e in items:
        print(f"{e['id']:6} {e['name']:16} {e['position']:19} {e['department']:10} "
              f"{e['salary']:>13,.2f}".replace(",", " "))


def main() -> None:
    print_employees("Усі працівники", employees)

    # пошук: list O(n) проти dict-index O(1)
    index = create_employee_index(employees)
    print("\nПошук E1007 у list :", find_employee_linear(employees, "E1007")["name"])
    print("Пошук E1007 у dict :", find_by_id(index, "E1007")["name"])
    print("Пошук E9999 у dict :", find_by_id(index, "E9999"))
    print("Пошук за ПІБ «енко»:", [e["name"] for e in find_by_name(employees, "енко")])

    # множини
    positions = get_positions(employees)
    print(f"\nУнікальних посад: {len(positions)} на {len(employees)} працівників")
    print("Відділи без працівників:", set(DEPARTMENTS) - get_used_departments(employees))

    # агрегація
    print()
    payroll = total_payroll(employees)
    print(f"Фонд оплати праці: {payroll:,.2f} грн".replace(",", " "))
    print(f"Середня зарплата: {average_salary(employees):,.2f} грн".replace(",", " "))
    top = highest_paid(employees)
    print(f"Максимальна зарплата: {top['id']} {top['name']} "
          f"{top['salary']:,.2f}".replace(",", " "))
    low, high = salary_range(employees)
    print(f"Діапазон зарплат (tuple): ({low}, {high})")

    # групування
    print("\nКількість за відділом (Counter):", dict(count_by_department(employees)))
    print("Групування за відділом (defaultdict):")
    for department, items in group_by_department(employees).items():
        print(f"  {department:8} -> {[e['id'] for e in items]}")
    print("Зведення відділ -> (кількість, фонд, середня):")
    for department, (count, total, avg) in department_summary(employees).items():
        print(f"  {department:8} {count}  {total:>12,.2f}  {avg:>11,.2f}".replace(",", " "))
    print("Вкладене групування, IT:", group_nested(employees)["IT"])

    # фільтрація та сортування
    print_employees("Зарплата >= 40 000, за спаданням зарплати",
                    sort_by_salary(filter_by_min_salary(employees, 40_000)))
    print_employees("Конвеєр: HR + Продажі, сортування відділ/зарплата",
                    pipeline(employees,
                             lambda d: filter_items(d, make_department_filter("HR", "Продажі")),
                             lambda d: sort_items(d, "department", "salary")))

    # *args, **kwargs
    print("\nsum_values(*args) для трьох зарплат:",
          sum_values(52_000.00, 78_500.00, 55_300.00))
    new_employee = create_employee(id="E1011", name="Богдан Кравець", position="Логіст",
                                   department="Логістика", salary=33_000.0)
    print("create_employee(**kwargs):", new_employee)

    path = export_summary(Path("output/summary.json"), payroll=payroll,
                          positions=sorted(positions),
                          by_department=dict(count_by_department(employees)))
    print(f"\nЗведення експортовано у {path.as_posix()}")
    print("Історія останніх операцій (deque, maxlen=5):")
    for number, record in enumerate(OPERATION_HISTORY, 1):
        print(f"  {number}. {record}")


if __name__ == "__main__":
    main()
