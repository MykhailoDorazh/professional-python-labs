"""Experiment: service creates its dependency itself (A) vs dependency injection (B)."""

from bank_domain.models import CurrentAccount, Customer
from bank_domain.protocols import Notifier
from bank_domain.services import ConsoleNotifier, InMemoryNotifier
from bank_domain.value_objects import Money


class DepositServiceA:
    """Variant A: concrete dependency is hard-coded."""

    def __init__(self) -> None:
        self.notifier = ConsoleNotifier()

    def deposit(self, account: CurrentAccount, amount: Money) -> None:
        account.deposit(amount)
        self.notifier.send(account.owner.email, f"Зараховано {amount}")


class DepositServiceB:
    """Variant B: dependency is injected and typed by the Notifier protocol."""

    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier

    def deposit(self, account: CurrentAccount, amount: Money) -> None:
        account.deposit(amount)
        self.notifier.send(account.owner.email, f"Зараховано {amount}")


def main() -> None:
    owner = Customer(1, "Іван Петренко", "ivan@example.com")

    print("Варіант A (жорстка залежність) - повідомлення лише друкуються, перевірити їх у тесті ніяк:")
    DepositServiceA().deposit(CurrentAccount("UA100001", owner), Money(100))

    print("\nВаріант B (DI) - у тесті підставляємо InMemoryNotifier і перевіряємо результат:")
    fake = InMemoryNotifier()
    DepositServiceB(fake).deposit(CurrentAccount("UA100002", owner), Money(100))
    print("    отримані повідомлення:", fake.messages)
    assert fake.messages == [("ivan@example.com", "Зараховано 100.00 UAH")]
    print("    перевірка пройдена; у production передаємо ConsoleNotifier або EmailNotifier")
    DepositServiceB(ConsoleNotifier()).deposit(CurrentAccount("UA100003", owner), Money(100))


if __name__ == "__main__":
    main()
