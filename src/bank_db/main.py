"""Demonstration of the persistence layer: CRUD, transactions, reports, DB-API."""

from __future__ import annotations

import argparse
from pathlib import Path

from bank_db.database import init_db, make_engine, make_session_factory
from bank_db.dbapi import find_account_by_number
from bank_db.exceptions import BankError
from bank_db.money import fmt
from bank_db.services import BankService


def print_accounts(service: BankService) -> None:
    print(f"  {'Рахунок':<12}{'Клієнт':<18}{'Тип':<9}{'Баланс, грн':>14}")
    for account in service.accounts.get_all():
        print(
            f"  {account.number:<12}{account.client.full_name:<18}"
            f"{account.account_type:<9}{fmt(account.balance_cents):>14}"
        )


def attempt(title: str, action: object) -> None:
    try:
        action()  # type: ignore[operator]
        print(f"  [OK]    {title}")
    except BankError as error:
        print(f"  [ERROR] {title}: {type(error).__name__}: {error}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Bank persistence layer demo")
    parser.add_argument("--db", default="demo.db", help="SQLite file for the demo")
    parser.add_argument("--echo", action="store_true", help="print SQL of the transfer")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    db_path.unlink(missing_ok=True)
    engine = make_engine(f"sqlite:///{db_path}")
    init_db(engine)
    Session = make_session_factory(engine)

    with Session() as session:
        bank = BankService(session)
        print("== 1. Create: клієнти і рахунки ==")
        koval = bank.register_client("Олена Коваль", "koval@example.com")
        melnyk = bank.register_client("Андрій Мельник")
        bondar = bank.register_client("Ірина Бондар")
        bank.open_account(koval.id, "UA00000001", "5000")
        bank.open_account(koval.id, "UA00000002", "12000", "savings")
        bank.open_account(melnyk.id, "UA00000003", "800.50")
        bank.open_account(bondar.id, "UA00000004")
        print_accounts(bank)

        print("\n== 2. Update: поповнення / списання ==")
        attempt("deposit 1500 -> UA00000003", lambda: bank.deposit("UA00000003", "1500"))
        attempt("withdraw 300 <- UA00000001", lambda: bank.withdraw("UA00000001", "300"))
        attempt("withdraw 10000 <- UA00000003", lambda: bank.withdraw("UA00000003", "10000"))
        attempt("deposit -5 -> UA00000001", lambda: bank.deposit("UA00000001", "-5"))
        attempt("duplicate UA00000001", lambda: bank.open_account(melnyk.id, "UA00000001"))

        print("\n== 3. transfer_money(): COMMIT ==")
        engine.echo = args.echo
        attempt(
            "2000 UA00000002 -> UA00000004",
            lambda: bank.transfer_money("UA00000002", "UA00000004", "2000"),
        )
        engine.echo = False
        print("\n== 4. transfer_money(): ROLLBACK ==")
        before = bank.get_balance("UA00000001")
        attempt(
            "1000 UA00000001 -> UA99999999",
            lambda: bank.transfer_money("UA00000001", "UA99999999", "1000"),
        )
        attempt(
            "99999 UA00000001 -> UA00000003",
            lambda: bank.transfer_money("UA00000001", "UA00000003", "99999"),
        )
        print(f"  Баланс UA00000001 до: {before}, після: {bank.get_balance('UA00000001')}")
        print_accounts(bank)

        print("\n== 5. Read: історія операцій UA00000002 ==")
        for tx in bank.history("UA00000002"):
            print(
                f"  #{tx.id:<3}{tx.kind:<13}{fmt(tx.amount_cents):>10}"
                f"  баланс {fmt(tx.balance_after_cents):>10}  {tx.counterparty or ''}"
            )

        print("\n== 6. Звіти (SUM / COUNT / AVG / GROUP BY / JOIN) ==")
        print(f"  Загальна сума коштів: {bank.total_funds()} грн")
        print(f"  Оборот: {bank.turnover()} грн")
        for kind, count, total, avg in bank.transactions.stats_by_kind():
            print(f"  {kind:<13} count={count}  sum={fmt(total)}  avg={avg / 100:.2f}")
        for name, count, money in bank.client_summary():
            print(f"  {name:<16} рахунків: {count}  сума: {money} грн")

        print("\n== 7. Update/Delete: CRUD клієнта і рахунку ==")
        bank.rename_client(melnyk.id, "Андрій Мельник-Шевченко")
        bank.open_account(bondar.id, "UA00000005")
        bank.close_account("UA00000005")
        print(f"  Перейменовано: {bank.get_client(melnyk.id).full_name}")
        print(f"  UA00000005 закрито, рахунків у БД: {bank.accounts.count()}")
        attempt("close UA00000002 (є кошти)", lambda: bank.close_account("UA00000002"))

    print("\n== 8. DB-API (sqlite3), parameterized query ==")
    print(" ", find_account_by_number(db_path, "UA00000002"))
    print("  injection \"' OR '1'='1\":", find_account_by_number(db_path, "' OR '1'='1"))
    engine.dispose()


if __name__ == "__main__":
    main()
