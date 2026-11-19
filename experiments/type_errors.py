"""Type-checking experiment: three intentional errors (run: mypy experiments/type_errors.py)."""

from bank_domain.models import Account, Customer
from bank_domain.repositories import InMemoryRepository

# Error 1: рядок замість int
customer_id: int = "1"


# Error 2: функція обіцяє int, а повертає str
def total() -> int:
    return "100"


# Error 3: у репозиторій рахунків додається клієнт
repository: InMemoryRepository[Account] = InMemoryRepository()
repository.add(Customer(1, "Іван Петренко", "ivan@example.com"))
