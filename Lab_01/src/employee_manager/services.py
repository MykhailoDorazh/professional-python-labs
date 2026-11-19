"""Business logic of the employee management system."""

from employee_manager.exceptions import EmployeeNotFoundError, InvalidEmployeeError
from employee_manager.models import Employee, validate_salary


def add_employee(employees: list[Employee], employee: Employee) -> Employee:
    """Add a new employee. Employee ids must be unique."""
    if any(e.employee_id == employee.employee_id for e in employees):
        raise InvalidEmployeeError(f"Працівник {employee.employee_id} вже існує")
    employees.append(employee)
    return employee


def find_employee(employees: list[Employee], employee_id: str) -> Employee:
    """Find an employee by id (case-insensitive)."""
    key = employee_id.strip().upper()
    for employee in employees:
        if employee.employee_id == key:
            return employee
    raise EmployeeNotFoundError(f"Працівника {key} не знайдено")


def find_by_department(employees: list[Employee], department: str) -> list[Employee]:
    """All employees of the department (case-insensitive)."""
    name = department.strip().lower()
    return [e for e in employees if e.department.lower() == name]


def search_employees(
    employees: list[Employee],
    name_part: str = "",
    department: str | None = None,
    min_salary: float | None = None,
    max_salary: float | None = None,
) -> list[Employee]:
    """Search by several criteria: part of the name, department and salary range."""
    text = name_part.strip().lower()
    result = [e for e in employees if text in e.name.lower()]
    if department:
        result = find_by_department(result, department)
    if min_salary is not None:
        result = [e for e in result if e.salary >= min_salary]
    if max_salary is not None:
        result = [e for e in result if e.salary <= max_salary]
    return result


def change_salary(employee: Employee, new_salary: float) -> float:
    """Set a new salary (validated). Returns the new value."""
    employee.salary = validate_salary(new_salary)
    return employee.salary


def change_position(employee: Employee, position: str) -> None:
    if not position.strip():
        raise InvalidEmployeeError("Посада не може бути порожньою")
    employee.position = position.strip()


def transfer(employee: Employee, department: str) -> None:
    """Move the employee to another department."""
    if not department.strip():
        raise InvalidEmployeeError("Відділ не може бути порожнім")
    employee.department = department.strip()


def total_payroll(employees: list[Employee]) -> float:
    """Monthly payroll fund: sum of all salaries."""
    return round(sum(e.salary for e in employees), 2)


def average_salary(employees: list[Employee]) -> float:
    """Average salary; 0 for an empty list."""
    return round(total_payroll(employees) / len(employees), 2) if employees else 0.0


def highest_paid(employees: list[Employee]) -> Employee | None:
    """Employee with the maximum salary (None for an empty list)."""
    return max(employees, key=lambda e: e.salary, default=None)


def sort_employees(employees: list[Employee], by: str = "salary",
                   descending: bool = True) -> list[Employee]:
    """Sort by salary, name, department or id."""
    keys = {
        "salary": lambda e: e.salary,
        "name": lambda e: e.name.lower(),
        "department": lambda e: (e.department.lower(), e.name.lower()),
        "id": lambda e: e.employee_id,
    }
    if by not in keys:
        raise ValueError(f"Невідоме поле сортування: {by}")
    return sorted(employees, key=keys[by], reverse=descending)


def calculate_statistics(employees: list[Employee]) -> dict[str, float]:
    """Count, payroll, average, minimum and maximum salary."""
    if not employees:
        return {"count": 0, "payroll": 0.0, "average": 0.0, "minimum": 0.0, "maximum": 0.0}
    salaries = [e.salary for e in employees]
    return {
        "count": len(salaries),
        "payroll": total_payroll(employees),
        "average": average_salary(employees),
        "minimum": min(salaries),
        "maximum": max(salaries),
    }


def department_summary(employees: list[Employee]) -> dict[str, tuple[int, float]]:
    """Department -> (number of employees, payroll), sorted by department name."""
    summary: dict[str, tuple[int, float]] = {}
    for e in sorted(employees, key=lambda e: e.department.lower()):
        count, payroll = summary.get(e.department, (0, 0.0))
        summary[e.department] = (count + 1, round(payroll + e.salary, 2))
    return summary
