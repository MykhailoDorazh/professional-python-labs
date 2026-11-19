"""Console input/output helpers: tables, validated keyboard input."""

import sys

from bank_accounts.config import CURRENCY
from bank_accounts.models import Account


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
        text = ask(prompt).replace(",", ".")
        try:
            return float(text)
        except ValueError:
            print("  Помилка: введіть число, наприклад 250.50")


def print_accounts(accounts: list[Account], title: str = "Рахунки") -> None:
    """Print accounts as a table."""
    print(f"\n{title}:")
    if not accounts:
        print("  (немає рахунків)")
        return
    print(f"  {'Номер':<10}{'Клієнт':<22}{'Баланс, ' + CURRENCY:>16}")
    print("  " + "-" * 48)
    for account in accounts:
        print(
            f"  {account.account_number:<10}"
            f"{account.client_name:<22}"
            f"{account.balance:>16,.2f}".replace(",", " ")
        )


def print_statistics(stats: dict[str, float]) -> None:
    """Print statistical indicators of balances."""
    print("\nСтатистика балансів:")
    print(f"  кількість рахунків: {stats['count']}")
    print(f"  загальна сума:      {stats['total']:,.2f} {CURRENCY}".replace(",", " "))
    print(f"  середній баланс:    {stats['average']:,.2f} {CURRENCY}".replace(",", " "))
    print(f"  мінімальний:        {stats['minimum']:,.2f} {CURRENCY}".replace(",", " "))
    print(f"  максимальний:       {stats['maximum']:,.2f} {CURRENCY}".replace(",", " "))
