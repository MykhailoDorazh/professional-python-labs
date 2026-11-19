"""Entry point: analysis of the bank accounts system."""

from pathlib import Path

from bank_analytics.analytics import (
    average_balance,
    balance_range,
    create_account,
    export_summary,
    richest_account,
    sum_values,
    total_balance,
    type_summary,
)
from bank_analytics.data import ACCOUNT_TYPES, accounts
from bank_analytics.decorators import OPERATION_HISTORY
from bank_analytics.processors import (
    count_by_type,
    create_account_index,
    filter_by_min_balance,
    filter_items,
    find_account_linear,
    find_by_number,
    get_unique_clients,
    group_by_type,
    group_nested,
    make_type_filter,
    pipeline,
    sort_by_balance,
    sort_items,
)


def print_accounts(title: str, items: list[dict]) -> None:
    print(f"\n{title}")
    print("-" * 58)
    for a in items:
        print(f"{a['number']:9} {a['client']:16} {a['type']:11} {a['balance']:>14,.2f}"
              .replace(",", " "))


def main() -> None:
    print_accounts("Усі рахунки", accounts)

    # пошук: list O(n) проти dict-index O(1)
    index = create_account_index(accounts)
    print("\nПошук UA100007 у list :", find_account_linear(accounts, "UA100007")["client"])
    print("Пошук UA100007 у dict :", find_by_number(index, "UA100007")["client"])
    print("Пошук UA999999 у dict :", find_by_number(index, "UA999999"))

    # множини
    clients = get_unique_clients(accounts)
    print(f"\nУнікальних клієнтів: {len(clients)} з {len(accounts)} рахунків")
    print("Типи без рахунків:", set(ACCOUNT_TYPES) - {a["type"] for a in accounts} or "немає")

    # агрегація
    print()
    total = total_balance(accounts)
    print(f"Загальна сума коштів: {total:,.2f} грн".replace(",", " "))
    print(f"Середній баланс: {average_balance(accounts):,.2f} грн".replace(",", " "))
    richest = richest_account(accounts)
    print(f"Найбільший баланс: {richest['number']} {richest['client']} "
          f"{richest['balance']:,.2f}".replace(",", " "))
    low, high = balance_range(accounts)
    print(f"Діапазон балансів (tuple): ({low}, {high})")

    # групування
    print("\nКількість за типом (Counter):", dict(count_by_type(accounts)))
    print("Групування за типом (defaultdict):")
    for type_, items in group_by_type(accounts).items():
        print(f"  {type_:11} -> {[a['number'] for a in items]}")
    print("Зведення type -> (кількість, сума, середнє):")
    for type_, (count, s, avg) in type_summary(accounts).items():
        print(f"  {type_:11} {count}  {s:>12,.2f}  {avg:>12,.2f}".replace(",", " "))
    print("Вкладене групування, депозитні:", group_nested(accounts)["депозитний"])

    # фільтрація та сортування
    print_accounts("Баланс >= 20 000, за спаданням балансу",
                   sort_by_balance(filter_by_min_balance(accounts, 20_000)))
    print_accounts("Конвеєр: поточні + зарплатні, сортування клієнт/баланс",
                   pipeline(accounts,
                            lambda d: filter_items(d, make_type_filter("поточний", "зарплатний")),
                            lambda d: sort_items(d, "client", "balance")))

    # *args, **kwargs
    print("\nsum_values(*args) для трьох балансів:",
          sum_values(48_300.50, 23_400.00, 12_500.00))
    new_account = create_account(number="UA100011", client="Софія Лисенко",
                                 balance=5_000.0, type="поточний")
    print("create_account(**kwargs):", new_account)

    path = export_summary(Path("output/summary.json"), total=total,
                          clients=sorted(clients), by_type=dict(count_by_type(accounts)))
    print(f"\nЗведення експортовано у {path.as_posix()}")
    print("Історія останніх операцій (deque, maxlen=5):")
    for number, record in enumerate(OPERATION_HISTORY, 1):
        print(f"  {number}. {record}")


if __name__ == "__main__":
    main()
