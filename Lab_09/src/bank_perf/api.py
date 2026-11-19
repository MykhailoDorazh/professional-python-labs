"""FastAPI REST API of the bank: HTTP + JSON over Service and Repository layers."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from bank_perf import __version__
from bank_perf.database import DATABASE_URL, init_db, make_engine, make_session_factory
from bank_perf.exceptions import (
    AccountNotEmptyError,
    AccountNotFoundError,
    BankError,
    ClientNotFoundError,
    DuplicateAccountError,
    InsufficientFundsError,
    InvalidAmountError,
)
from bank_perf.models import Account, Client, Transaction
from bank_perf.schemas import (
    AccountCreate,
    AccountOverview,
    AccountResponse,
    AccountUpdate,
    ClientCreate,
    ClientResponse,
    ErrorResponse,
    MoneyOperation,
    OperationResponse,
    OverviewRequest,
    OverviewResponse,
    StatsResponse,
    TransactionResponse,
    TransferCreate,
    TransferResponse,
)
from bank_perf.services import BankService

ERROR_STATUS: dict[type[BankError], int] = {
    AccountNotFoundError: status.HTTP_404_NOT_FOUND,
    ClientNotFoundError: status.HTTP_404_NOT_FOUND,
    DuplicateAccountError: status.HTTP_409_CONFLICT,
    InsufficientFundsError: status.HTTP_409_CONFLICT,
    AccountNotEmptyError: status.HTTP_409_CONFLICT,
    InvalidAmountError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}
ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Ресурс не знайдено"},
    409: {"model": ErrorResponse, "description": "Конфлікт із бізнес-правилами"},
}
OVERVIEW_CONCURRENCY = 4  # at most 4 DB reads at the same time
OVERVIEW_TIMEOUT = 5.0  # seconds for the whole batch


# ---------- application factory ----------
def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or DATABASE_URL

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(url)
        init_db(engine)
        app.state.session_factory = make_session_factory(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="Bank Accounts API",
        version=__version__,
        description="REST API системи банківських рахунків (ЛР №8, варіант 4).",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "clients", "description": "Клієнти банку"},
            {"name": "accounts", "description": "Рахунки, баланс, історія операцій"},
            {"name": "operations", "description": "Поповнення, списання, перекази"},
            {"name": "reports", "description": "Статистика та асинхронна агрегація"},
        ],
    )

    @app.exception_handler(BankError)
    async def bank_error_handler(_: Request, error: BankError) -> JSONResponse:
        code = next(
            (c for cls, c in ERROR_STATUS.items() if isinstance(error, cls)),
            status.HTTP_400_BAD_REQUEST,
        )
        body = ErrorResponse(error=type(error).__name__, detail=str(error))
        return JSONResponse(status_code=code, content=body.model_dump())

    app.include_router(build_router())
    return app


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session


def get_service(session: Annotated[Session, Depends(get_session)]) -> BankService:
    return BankService(session)


ServiceDep = Annotated[BankService, Depends(get_service)]


def build_router() -> APIRouter:
    router = APIRouter()

    # ---------- meta ----------
    @router.get("/", tags=["reports"])
    async def root() -> dict[str, str]:
        return {"message": "Bank Accounts API is running", "docs": "/docs"}

    @router.get("/health", tags=["reports"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    # ---------- clients ----------
    @router.post("/clients", response_model=ClientResponse,
                 status_code=status.HTTP_201_CREATED, tags=["clients"])
    def create_client(data: ClientCreate, bank: ServiceDep) -> Client:
        return bank.register_client(data.full_name, data.email)

    @router.get("/clients/{client_id}", response_model=ClientResponse,
                tags=["clients"], responses=ERRORS)
    def get_client(client_id: int, bank: ServiceDep) -> Client:
        return bank.get_client(client_id)

    @router.get("/clients/{client_id}/accounts", response_model=list[AccountResponse],
                tags=["clients"], responses=ERRORS)
    def client_accounts(client_id: int, bank: ServiceDep) -> list[Account]:
        return bank.get_client(client_id).accounts

    # ---------- accounts ----------
    @router.post("/accounts", response_model=AccountResponse,
                 status_code=status.HTTP_201_CREATED, tags=["accounts"], responses=ERRORS)
    def create_account(data: AccountCreate, bank: ServiceDep) -> Account:
        bank.get_client(data.client_id)  # 404 instead of FK error
        return bank.open_account(data.client_id, data.number, data.initial_deposit,
                                 data.account_type)

    @router.get("/accounts", response_model=list[AccountResponse], tags=["accounts"])
    def list_accounts(
        bank: ServiceDep,
        client_id: Annotated[int | None, Query(gt=0)] = None,
        number: Annotated[str | None, Query(description="Пошук за номером")] = None,
        min_balance: Annotated[float | None, Query(ge=0)] = None,
        account_type: Annotated[str | None, Query(pattern="^(current|savings)$")] = None,
        sort_by_balance: bool = False,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Account]:
        accounts = bank.accounts.filter(
            min_balance_cents=None if min_balance is None else round(min_balance * 100),
            account_type=account_type,
            order_by_balance=sort_by_balance,
        )
        if client_id is not None:
            accounts = [a for a in accounts if a.client_id == client_id]
        if number is not None:
            accounts = [a for a in accounts if number.upper() in a.number]
        return accounts[offset:offset + limit]

    @router.get("/accounts/{account_id}", response_model=AccountResponse,
                tags=["accounts"], responses=ERRORS)
    def get_account(account_id: int, bank: ServiceDep) -> Account:
        return bank.get_account_by_id(account_id)

    @router.patch("/accounts/{account_id}", response_model=AccountResponse,
                  tags=["accounts"], responses=ERRORS)
    def update_account(account_id: int, data: AccountUpdate, bank: ServiceDep) -> Account:
        account = bank.get_account_by_id(account_id)
        if data.account_type is not None:
            account = bank.change_account_type(account.number, data.account_type)
        return account

    @router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT,
                   tags=["accounts"], responses=ERRORS)
    def delete_account(account_id: int, bank: ServiceDep) -> None:
        bank.close_account(bank.get_account_by_id(account_id).number)

    @router.get("/accounts/{account_id}/transactions",
                response_model=list[TransactionResponse], tags=["accounts"], responses=ERRORS)
    def account_transactions(
        account_id: int,
        bank: ServiceDep,
        kind: Annotated[str | None, Query(
            pattern="^(deposit|withdraw|transfer_in|transfer_out)$")] = None,
    ) -> list[Transaction]:
        history = bank.history(bank.get_account_by_id(account_id).number)
        return [t for t in history if kind is None or t.kind == kind]

    # ---------- operations ----------
    @router.post("/accounts/{account_id}/deposit", response_model=OperationResponse,
                 tags=["operations"], responses=ERRORS)
    def deposit(account_id: int, data: MoneyOperation, bank: ServiceDep) -> OperationResponse:
        account = bank.get_account_by_id(account_id)
        tx = bank.deposit(account.number, data.amount)
        return OperationResponse(account=AccountResponse.model_validate(account),
                                 transaction=TransactionResponse.model_validate(tx))

    @router.post("/accounts/{account_id}/withdraw", response_model=OperationResponse,
                 tags=["operations"], responses=ERRORS)
    def withdraw(account_id: int, data: MoneyOperation, bank: ServiceDep) -> OperationResponse:
        account = bank.get_account_by_id(account_id)
        tx = bank.withdraw(account.number, data.amount)
        return OperationResponse(account=AccountResponse.model_validate(account),
                                 transaction=TransactionResponse.model_validate(tx))

    @router.post("/transfers", response_model=TransferResponse,
                 status_code=status.HTTP_201_CREATED, tags=["operations"], responses=ERRORS)
    def transfer(data: TransferCreate, bank: ServiceDep) -> TransferResponse:
        bank.transfer_money(data.from_account, data.to_account, data.amount)
        return TransferResponse(
            from_account=AccountResponse.model_validate(bank.get_account(data.from_account)),
            to_account=AccountResponse.model_validate(bank.get_account(data.to_account)),
            amount=data.amount,
        )

    # ---------- reports ----------
    @router.get("/stats", response_model=StatsResponse, tags=["reports"])
    def stats(bank: ServiceDep) -> StatsResponse:
        return StatsResponse(clients=bank.clients.count(), accounts=bank.accounts.count(),
                             total_funds=bank.total_funds(), turnover=bank.turnover())

    @router.post("/accounts/overview", response_model=OverviewResponse, tags=["reports"])
    async def accounts_overview(data: OverviewRequest, request: Request) -> OverviewResponse:
        """Balances and recent history of several accounts, loaded concurrently.

        Every account is read by its own asyncio.Task in a worker thread with its own
        session; a Semaphore limits parallel DB reads, wait_for limits total time.
        """
        factory: sessionmaker[Session] = request.app.state.session_factory
        semaphore = asyncio.Semaphore(OVERVIEW_CONCURRENCY)
        started = time.perf_counter()

        def load(account_id: int) -> AccountOverview:
            with factory() as session:
                bank = BankService(session)
                try:
                    account = bank.get_account_by_id(account_id)
                except AccountNotFoundError as error:
                    return AccountOverview(account_id=account_id, ok=False, error=str(error))
                history = bank.history(account.number)[-data.history_limit:] \
                    if data.history_limit else []
                return AccountOverview(
                    account_id=account_id, ok=True,
                    account=AccountResponse.model_validate(account),
                    last_transactions=[TransactionResponse.model_validate(t) for t in history],
                )

        async def load_limited(account_id: int) -> AccountOverview:
            async with semaphore:
                return await asyncio.to_thread(load, account_id)

        tasks = [asyncio.create_task(load_limited(i)) for i in data.account_ids]
        try:
            items = await asyncio.wait_for(asyncio.gather(*tasks), timeout=OVERVIEW_TIMEOUT)
        except TimeoutError as error:
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT,
                                "Batch operation timed out") from error
        return OverviewResponse(
            requested=len(items), succeeded=sum(i.ok for i in items),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2), items=list(items),
        )

    return router


app = create_app()
