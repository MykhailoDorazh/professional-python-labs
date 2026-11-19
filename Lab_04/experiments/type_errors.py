"""Type-checking experiment: three intentional errors (run: mypy experiments/type_errors.py)."""

from employee_domain.models import Department, Employee
from employee_domain.repositories import InMemoryRepository

# Error 1: рядок замість float
salary: float = "52000"


# Error 2: функція обіцяє int, а повертає str
def headcount() -> int:
    return "5"


# Error 3: у репозиторій працівників додається відділ
repository: InMemoryRepository[Employee] = InMemoryRepository()
repository.add(Department("IT", "Інформаційні технології"))
