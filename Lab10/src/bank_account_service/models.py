"""SQLAlchemy ORM models: clients 1─N accounts 1─N transactions."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    accounts: Mapped[list[Account]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="Account.id",
    )

    def __repr__(self) -> str:
        return f"Client(id={self.id}, full_name={self.full_name!r})"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("balance_cents >= 0", name="ck_accounts_balance_non_negative"),
        CheckConstraint("account_type IN ('current', 'savings')", name="ck_accounts_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    balance_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Added by migration 0002_add_account_type.
    account_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="current", server_default="current"
    )

    client: Mapped[Client] = relationship(back_populates="accounts")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="Transaction.id",
    )

    def __repr__(self) -> str:
        return f"Account(number={self.number!r}, balance_cents={self.balance_cents})"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
        CheckConstraint(
            "kind IN ('deposit', 'withdraw', 'transfer_in', 'transfer_out')",
            name="ck_transactions_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    account: Mapped[Account] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"Transaction({self.kind}, {self.amount_cents})"
