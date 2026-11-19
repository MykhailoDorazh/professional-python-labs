"""External payloads (TypedDict) and their mapping to domain objects."""

from typing import Literal, NotRequired, TypedDict

from bank_domain.models import Account, CurrentAccount, Customer, SavingsAccount
from bank_domain.value_objects import Money


class AccountPayload(TypedDict):
    """JSON-like account data from an external system (still a plain dict)."""

    number: str
    type: Literal["savings", "current"]
    owner_id: int
    owner_name: str
    owner_email: str
    balance: float
    currency: str
    interest_rate: NotRequired[float]
    monthly_fee: NotRequired[float]


class SummaryPayload(TypedDict):
    accounts: int
    total: float
    currency: str
    by_type: dict[str, float]


def account_from_payload(data: AccountPayload) -> Account:
    """Payload -> domain object (validation happens in the constructors)."""
    owner = Customer(data["owner_id"], data["owner_name"], data["owner_email"])
    balance = Money(data["balance"], data["currency"])
    if data["type"] == "savings":
        return SavingsAccount(data["number"], owner, balance,
                              interest_rate=data.get("interest_rate", 0.01))
    return CurrentAccount(data["number"], owner, balance,
                          monthly_fee=Money(data.get("monthly_fee", 25.0), data["currency"]))


def account_to_payload(account: Account) -> AccountPayload:
    payload: AccountPayload = {
        "number": account.number,
        "type": "savings" if isinstance(account, SavingsAccount) else "current",
        "owner_id": account.owner.id,
        "owner_name": account.owner.name,
        "owner_email": account.owner.email,
        "balance": account.balance.amount,
        "currency": account.balance.currency,
    }
    if isinstance(account, SavingsAccount):
        payload["interest_rate"] = account.interest_rate
    elif isinstance(account, CurrentAccount):
        payload["monthly_fee"] = account.monthly_fee.amount
    return payload
