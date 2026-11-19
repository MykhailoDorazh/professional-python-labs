"""Demo data for the API: three clients, five accounts, some history."""

from __future__ import annotations

from bank_perf.database import init_db, make_engine, make_session_factory
from bank_perf.services import BankService


def seed(url: str) -> None:
    engine = make_engine(url)
    init_db(engine)
    with make_session_factory(engine)() as session:
        bank = BankService(session)
        if bank.clients.count():
            return
        koval = bank.register_client("Олена Коваль", "koval@example.com")
        melnyk = bank.register_client("Андрій Мельник")
        bondar = bank.register_client("Ірина Бондар")
        bank.open_account(koval.id, "UA00000001", "5000")
        bank.open_account(koval.id, "UA00000002", "12000", "savings")
        bank.open_account(melnyk.id, "UA00000003", "800.50")
        bank.open_account(bondar.id, "UA00000004", "250")
        bank.open_account(bondar.id, "UA00000005", "3000", "savings")
        bank.deposit("UA00000003", "1500")
        bank.withdraw("UA00000001", "300")
        bank.transfer_money("UA00000002", "UA00000004", "2000")
    engine.dispose()
