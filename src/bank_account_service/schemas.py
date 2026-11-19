"""Pydantic schemas: validation of requests and serialization of responses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from bank_account_service.money import from_cents

Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, examples=["1500.00"])]
AccountNumber = Annotated[
    str, Field(pattern=r"^UA\d{8}$", examples=["UA00000001"], description="UA + 8 цифр")
]
AccountType = Literal["current", "savings"]


# ---------- requests ----------
class ClientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100, examples=["Олена Коваль"])
    email: EmailStr | None = None

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ім'я не може складатися з пробілів")
        return value.strip()


class AccountCreate(BaseModel):
    client_id: int = Field(gt=0)
    number: AccountNumber
    account_type: AccountType = "current"
    initial_deposit: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)] = Decimal(0)


class AccountUpdate(BaseModel):
    account_type: AccountType | None = None


class MoneyOperation(BaseModel):
    amount: Money


class TransferCreate(BaseModel):
    from_account: AccountNumber
    to_account: AccountNumber
    amount: Money


class OverviewRequest(BaseModel):
    account_ids: list[int] = Field(min_length=1, max_length=100)
    history_limit: int = Field(default=3, ge=0, le=50)


# ---------- responses ----------
class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str | None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    client_id: int
    account_type: str
    balance_cents: int = Field(exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def balance(self) -> Decimal:
        return from_cents(self.balance_cents)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    amount_cents: int = Field(exclude=True)
    balance_after_cents: int = Field(exclude=True)
    counterparty: str | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def amount(self) -> Decimal:
        return from_cents(self.amount_cents)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def balance_after(self) -> Decimal:
        return from_cents(self.balance_after_cents)


class OperationResponse(BaseModel):
    account: AccountResponse
    transaction: TransactionResponse


class TransferResponse(BaseModel):
    from_account: AccountResponse
    to_account: AccountResponse
    amount: Decimal


class StatsResponse(BaseModel):
    clients: int
    accounts: int
    total_funds: Decimal
    turnover: Decimal


class AccountOverview(BaseModel):
    account_id: int
    ok: bool
    account: AccountResponse | None = None
    last_transactions: list[TransactionResponse] = []
    error: str | None = None


class OverviewResponse(BaseModel):
    requested: int
    succeeded: int
    elapsed_ms: float
    items: list[AccountOverview]


class ErrorResponse(BaseModel):
    error: str
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    environment: str
    database: Literal["ok", "unavailable"]


class ForecastResponse(BaseModel):
    accounts: int
    total_now: Decimal
    total_in_one_year: Decimal
