"""Type-checking experiment after corrections (run: mypy experiments/type_errors_fixed.py)."""

from bank_domain.models import Account, CurrentAccount, Customer
from bank_domain.repositories import InMemoryRepository
from bank_domain.value_objects import Money

# Fix 1: значення має тип int
customer_id: int = 1


# Fix 2: повертаємо int
def total() -> int:
    return 100


# Fix 3: у репозиторій рахунків додається рахунок, клієнт - його складова частина
repository: InMemoryRepository[Account] = InMemoryRepository()
owner = Customer(customer_id, "Іван Петренко", "ivan@example.com")
repository.add(CurrentAccount("UA100001", owner, Money(total())))
