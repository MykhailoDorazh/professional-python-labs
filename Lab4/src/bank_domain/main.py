"""Demo scenario of the typed bank domain model."""

from bank_domain.dto import AccountPayload, account_from_payload, account_to_payload
from bank_domain.exceptions import BankError
from bank_domain.models import Account, CurrentAccount, Customer, SavingsAccount
from bank_domain.protocols import HasKey
from bank_domain.repositories import InMemoryRepository
from bank_domain.services import BankService, ConsoleNotifier, ReportService, clamp
from bank_domain.value_objects import Money


def build_application() -> tuple[BankService, ReportService, InMemoryRepository[Account]]:
    """Manual dependency-injection container: all wiring is in one place."""
    repository = InMemoryRepository[Account]()
    service = BankService(accounts=repository, notifier=ConsoleNotifier())
    reports = ReportService(accounts=repository)
    return service, reports, repository


def main() -> None:
    service, reports, repository = build_application()

    ivan = Customer(1, "Іван Петренко", "ivan@example.com")
    olena = Customer(2, "Олена Коваль", "olena@example.com")

    print("1. Відкриття рахунків:")
    service.open_account(SavingsAccount("UA100001", ivan, Money(50_000),
                                        interest_rate=0.01, minimum_balance=Money(1_000)))
    service.open_account(CurrentAccount("UA100002", ivan, Money(3_200)))
    payload: AccountPayload = {"number": "UA100003", "type": "current", "owner_id": 2,
                               "owner_name": "Олена Коваль", "owner_email": "olena@example.com",
                               "balance": 12_750.5, "currency": "UAH", "monthly_fee": 30.0}
    service.open_account(account_from_payload(payload))

    print("\n2. Операції:")
    service.deposit("UA100002", Money(1_800))
    service.withdraw("UA100003", Money(750.5))
    for number, amount in (("UA100002", 9_000), ("UA100001", 49_500), ("UA100009", 10)):
        try:
            service.withdraw(number, Money(amount))
        except BankError as error:
            print(f"    помилка {type(error).__name__}: {error}")
    try:
        Money(-5)
    except ValueError as error:
        print(f"    Money(-5) -> ValueError: {error}")

    print("\n3. Пошук і баланс:")
    print("   баланс UA100002:", service.get_balance("UA100002"))
    print("   рахунки Івана:", [str(a) for a in service.find_by_owner("іван")])

    print("\n4. Dunder methods:")
    account = service.find_account("UA100002")
    print("   repr:", repr(account))
    print("   len(account) =", len(account), "| 'UA100003' in repository:", "UA100003" in repository)
    for transaction in account:
        print("  ", transaction)
    print("   Money(100) + Money(50.5) =", Money(100) + Money(50.5),
          "| Money(10) < Money(20):", Money(10) < Money(20))

    print("\n5. Закриття місяця (поліморфізм close_month):")
    for transaction in service.close_month():
        print("  ", transaction)

    print("\n6. Звіти:")
    print("   загальна сума коштів:", reports.total_funds())
    print("   за типами:", {k: str(v) for k, v in reports.totals_by_type().items()})
    print("   рейтинг:", [a.number for a in reports.ranking()])
    print("   summary (TypedDict):", reports.summary())

    print("\n7. Типи:")
    print("   isinstance(account, HasKey) [runtime_checkable]:", isinstance(account, HasKey))
    print("   clamp(15, 0, 10) =", clamp(15, 0, 10), "| clamp(0.25, 0.0, 0.1) =", clamp(0.25, 0.0, 0.1))
    print("   payload:", account_to_payload(repository["UA100003"]))
    print(f"   ivan == ivan2: {ivan == Customer(1, 'Іван Петренко', 'ivan@example.com')}"
          " (dataclass __eq__)")


if __name__ == "__main__":
    main()
