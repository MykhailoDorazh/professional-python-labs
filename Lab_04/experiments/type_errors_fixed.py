"""Type-checking experiment after corrections (run: mypy experiments/type_errors_fixed.py)."""

from employee_domain.models import Department, Employee
from employee_domain.repositories import InMemoryRepository
from employee_domain.value_objects import Money

# Fix 1: значення має тип float
salary: float = 52_000.0


# Fix 2: повертаємо int
def headcount() -> int:
    return 5


# Fix 3: працівник - у репозиторій працівників, відділ - у репозиторій відділів
repository: InMemoryRepository[Employee] = InMemoryRepository()
repository.add(Employee("E0001", "Іван Петренко", "Розробник", Money(salary)))
departments: InMemoryRepository[Department] = InMemoryRepository()
departments.add(Department("IT", "Інформаційні технології"))
