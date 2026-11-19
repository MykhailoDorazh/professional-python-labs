"""Application entry point: demo scenario and menu-driven interface."""

import sys

from bank_accounts.config import CURRENCY
from bank_accounts.console import (
    ask,
    ask_float,
    print_accounts,
    print_statistics,
)
from bank_accounts.exceptions import BankError
from bank_accounts.models import Account
from bank_accounts.services import (
    calculate_statistics,
    calculate_total,
    deposit,
    find_account,
    get_balance,
    open_account,
    search_accounts,
    sort_accounts,
    withdraw,
)


def create_demo_accounts() -> list[Account]:
    """Initial data set."""
    return [
        Account("Іван Петренко", "UA100001", 12_500.00),
        Account("Олена Коваль", "UA100002", 48_300.50),
        Account("Андрій Мельник", "UA100003", 2_150.75),
        Account("Марія Бондар", "UA100004", 91_000.00),
        Account("Олег Шевченко", "UA100005", 0.00),
    ]


def run_demo(accounts: list[Account]) -> None:
    """Non-interactive scenario that shows all features."""
    print_accounts(accounts, "Усі рахунки")

    account = find_account(accounts, "UA100003")
    print(f"\nПошук UA100003: {account.client_name}, "
          f"баланс {account.formatted_balance}")

    print(f"Поповнення на 850.25: новий баланс "
          f"{deposit(account, 850.25):.2f} {CURRENCY}")
    print(f"Списання 1 000.00: новий баланс "
          f"{withdraw(account, 1000):.2f} {CURRENCY}")

    try:
        withdraw(accounts[4], 100)
    except BankError as error:
        print(f"Списання 100.00 відхилено: {error}")

    try:
        find_account(accounts, "UA999999")
    except BankError as error:
        print(f"Пошук UA999999: {error}")

    print(f"Перевірка балансу UA100002: {get_balance(accounts[1]):.2f} {CURRENCY}")
    print(f"\nЗагальна сума коштів: {calculate_total(accounts):,.2f} {CURRENCY}"
          .replace(",", " "))

    rich = search_accounts(accounts, name_part="о", min_balance=10_000)
    print_accounts(rich, "Пошук: ім'я містить «о» і баланс >= 10 000")
    print_accounts(sort_accounts(accounts), "Сортування за балансом (спадання)")
    print_statistics(calculate_statistics(accounts))


def print_menu() -> None:
    print()
    print("===== Банківські рахунки =====")
    print("1. Показати всі рахунки")
    print("2. Знайти рахунок за номером")
    print("3. Поповнити рахунок")
    print("4. Зняти кошти")
    print("5. Відкрити новий рахунок")
    print("6. Пошук за клієнтом і балансом")
    print("7. Статистика і загальна сума")
    print("9. Показати меню")
    print("0. Вихід")


def handle_command(command: str, accounts: list[Account]) -> bool:
    """Execute one menu command. Returns False when the user exits."""
    if command == "1":
        print_accounts(sort_accounts(accounts, by="number", descending=False))
    elif command == "2":
        account = find_account(accounts, ask("Номер рахунку: "))
        print(f"  {account.client_name}: {account.formatted_balance}")
    elif command == "3":
        account = find_account(accounts, ask("Номер рахунку: "))
        balance = deposit(account, ask_float("Сума поповнення: "))
        print(f"  Успішно. Новий баланс: {balance:.2f} {CURRENCY}")
    elif command == "4":
        account = find_account(accounts, ask("Номер рахунку: "))
        balance = withdraw(account, ask_float("Сума списання: "))
        print(f"  Успішно. Новий баланс: {balance:.2f} {CURRENCY}")
    elif command == "5":
        account = open_account(
            accounts,
            ask("Ім'я клієнта: "),
            ask("Номер рахунку (UA + 6 цифр): "),
            ask_float("Початковий баланс: "),
        )
        print(f"  Відкрито рахунок {account.account_number}")
    elif command == "6":
        name = ask("Частина імені (Enter - усі): ")
        minimum = ask_float("Мінімальний баланс: ")
        print_accounts(search_accounts(accounts, name, minimum), "Результат пошуку")
    elif command == "7":
        print_statistics(calculate_statistics(accounts))
    elif command == "9":
        print_menu()
    elif command == "0":
        print("До побачення!")
        return False
    else:
        print("  Невідома команда (9 - показати меню)")
    return True


def run_menu(accounts: list[Account]) -> None:
    """Menu-driven interface with keyboard input."""
    print_menu()
    running = True
    while running:
        print()
        try:
            running = handle_command(ask("Оберіть команду: "), accounts)
        except BankError as error:
            print(f"  Помилка: {error}")
        except EOFError:
            break


def main() -> None:
    accounts = create_demo_accounts()
    if "--menu" in sys.argv[1:]:
        run_menu(accounts)
    else:
        run_demo(accounts)


if __name__ == "__main__":
    main()
