"""FastAPI REST API of the bank: HTTP + JSON over Service and Repository layers."""

from __future__ import annotations

import asyncio
import hmac
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from bank_account_service import __version__
from bank_account_service.analytics import RATE_BP, project_balances
from bank_account_service.config import Settings, get_settings
from bank_account_service.database import init_db, make_engine, make_session_factory
from bank_account_service.exceptions import (
    AccountNotEmptyError,
    AccountNotFoundError,
    BankError,
    ClientNotFoundError,
    DuplicateAccountError,
    InsufficientFundsError,
    InvalidAmountError,
)
from bank_account_service.models import Account, Client, Transaction
from bank_account_service.money import from_cents
from bank_account_service.schemas import (
    AccountCreate,
    AccountOverview,
    AccountResponse,
    AccountUpdate,
    ClientCreate,
    ClientResponse,
    ErrorResponse,
    ForecastResponse,
    HealthResponse,
    MoneyOperation,
    OperationResponse,
    OverviewRequest,
    OverviewResponse,
    StatsResponse,
    TransactionResponse,
    TransferCreate,
    TransferResponse,
)
from bank_account_service.services import BankService

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
log = logging.getLogger("bank_account_service.api")


# ---------- application factory ----------
def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application; all configuration comes from `Settings` (environment)."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url)
        if not settings.is_production:
            init_db(engine)  # production schema is managed only by Alembic migrations
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        log.info("%s %s started, env=%s", settings.app_name, __version__, settings.app_env)
        yield
        engine.dispose()
        log.info("shutdown complete")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="REST API системи банківських рахунків (ЛР №10, варіант 4).",
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

    @app.middleware("http")
    async def access_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        log.info(
            "%s %s -> %d (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    app.state.settings = settings
    app.include_router(build_router())
    return app


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session


def get_service(session: Annotated[Session, Depends(get_session)]) -> BankService:
    return BankService(session)


ServiceDep = Annotated[BankService, Depends(get_service)]


def require_api_key(request: Request, x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Admin endpoints need X-API-Key equal to the API_KEY secret from the environment."""
    expected = request.app.state.settings.api_key
    if expected is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin API is disabled: API_KEY is not set")
    if x_api_key is None or not hmac.compare_digest(x_api_key, expected.get_secret_value()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing X-API-Key")


def build_router() -> APIRouter:
    router = APIRouter()

    # ---------- meta ----------
    @router.get("/", tags=["reports"])
    async def root() -> dict[str, str]:
        return {"message": "Bank Accounts API is running", "docs": "/docs"}

    @router.get(
        "/health",
        response_model=HealthResponse,
        tags=["reports"],
        responses={503: {"model": HealthResponse}},
    )
    async def health(request: Request) -> JSONResponse:
        """Liveness + readiness: the process answers and the database is reachable."""
        settings: Settings = request.app.state.settings

        def ping() -> None:
            with request.app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

        try:
            await asyncio.to_thread(ping)
            database, code = "ok", status.HTTP_200_OK
        except Exception:
            log.exception("health check: database is not reachable")
            database, code = "unavailable", status.HTTP_503_SERVICE_UNAVAILABLE
        body = HealthResponse(
            status="ok" if code == 200 else "degraded",
            version=__version__,
            environment=settings.app_env,
            database=database,
        )
        return JSONResponse(status_code=code, content=body.model_dump())

    # ---------- clients ----------
    @router.post(
        "/clients",
        response_model=ClientResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["clients"],
    )
    def create_client(data: ClientCreate, bank: ServiceDep) -> Client:
        return bank.register_client(data.full_name, data.email)

    @router.get(
        "/clients/{client_id}", response_model=ClientResponse, tags=["clients"], responses=ERRORS
    )
    def get_client(client_id: int, bank: ServiceDep) -> Client:
        return bank.get_client(client_id)

    @router.get(
        "/clients/{client_id}/accounts",
        response_model=list[AccountResponse],
        tags=["clients"],
        responses=ERRORS,
    )
    def client_accounts(client_id: int, bank: ServiceDep) -> list[Account]:
        return bank.get_client(client_id).accounts

    # ---------- accounts ----------
    @router.post(
        "/accounts",
        response_model=AccountResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["accounts"],
        responses=ERRORS,
    )
    def create_account(data: AccountCreate, bank: ServiceDep) -> Account:
        bank.get_client(data.client_id)  # 404 instead of FK error
        return bank.open_account(
            data.client_id, data.number, data.initial_deposit, data.account_type
        )

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
        return accounts[offset : offset + limit]

    @router.get(
        "/accounts/{account_id}",
        response_model=AccountResponse,
        tags=["accounts"],
        responses=ERRORS,
    )
    def get_account(account_id: int, bank: ServiceDep) -> Account:
        return bank.get_account_by_id(account_id)

    @router.patch(
        "/accounts/{account_id}",
        response_model=AccountResponse,
        tags=["accounts"],
        responses=ERRORS,
    )
    def update_account(account_id: int, data: AccountUpdate, bank: ServiceDep) -> Account:
        account = bank.get_account_by_id(account_id)
        if data.account_type is not None:
            account = bank.change_account_type(account.number, data.account_type)
        return account

    @router.delete(
        "/accounts/{account_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["accounts"],
        responses=ERRORS,
        dependencies=[Depends(require_api_key)],
    )
    def delete_account(account_id: int, bank: ServiceDep) -> None:
        bank.close_account(bank.get_account_by_id(account_id).number)

    @router.get(
        "/accounts/{account_id}/transactions",
        response_model=list[TransactionResponse],
        tags=["accounts"],
        responses=ERRORS,
    )
    def account_transactions(
        account_id: int,
        bank: ServiceDep,
        kind: Annotated[
            str | None, Query(pattern="^(deposit|withdraw|transfer_in|transfer_out)$")
        ] = None,
    ) -> list[Transaction]:
        history = bank.history(bank.get_account_by_id(account_id).number)
        return [t for t in history if kind is None or t.kind == kind]

    # ---------- operations ----------
    @router.post(
        "/accounts/{account_id}/deposit",
        response_model=OperationResponse,
        tags=["operations"],
        responses=ERRORS,
    )
    def deposit(account_id: int, data: MoneyOperation, bank: ServiceDep) -> OperationResponse:
        account = bank.get_account_by_id(account_id)
        tx = bank.deposit(account.number, data.amount)
        return OperationResponse(
            account=AccountResponse.model_validate(account),
            transaction=TransactionResponse.model_validate(tx),
        )

    @router.post(
        "/accounts/{account_id}/withdraw",
        response_model=OperationResponse,
        tags=["operations"],
        responses=ERRORS,
    )
    def withdraw(account_id: int, data: MoneyOperation, bank: ServiceDep) -> OperationResponse:
        account = bank.get_account_by_id(account_id)
        tx = bank.withdraw(account.number, data.amount)
        return OperationResponse(
            account=AccountResponse.model_validate(account),
            transaction=TransactionResponse.model_validate(tx),
        )

    @router.post(
        "/transfers",
        response_model=TransferResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["operations"],
        responses=ERRORS,
    )
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
        return StatsResponse(
            clients=bank.clients.count(),
            accounts=bank.accounts.count(),
            total_funds=bank.total_funds(),
            turnover=bank.turnover(),
        )

    @router.post("/accounts/overview", response_model=OverviewResponse, tags=["reports"])
    async def accounts_overview(data: OverviewRequest, request: Request) -> OverviewResponse:
        """Balances and recent history of several accounts, loaded concurrently.

        Every account is read by its own asyncio.Task in a worker thread with its own
        session; a Semaphore limits parallel DB reads, wait_for limits total time.
        """
        factory: sessionmaker[Session] = request.app.state.session_factory
        settings: Settings = request.app.state.settings
        semaphore = asyncio.Semaphore(settings.overview_concurrency)
        started = time.perf_counter()

        def load(account_id: int) -> AccountOverview:
            with factory() as session:
                bank = BankService(session)
                try:
                    account = bank.get_account_by_id(account_id)
                except AccountNotFoundError as error:
                    return AccountOverview(account_id=account_id, ok=False, error=str(error))
                history = (
                    bank.history(account.number)[-data.history_limit :]
                    if data.history_limit
                    else []
                )
                return AccountOverview(
                    account_id=account_id,
                    ok=True,
                    account=AccountResponse.model_validate(account),
                    last_transactions=[TransactionResponse.model_validate(t) for t in history],
                )

        async def load_limited(account_id: int) -> AccountOverview:
            async with semaphore:
                return await asyncio.to_thread(load, account_id)

        tasks = [asyncio.create_task(load_limited(i)) for i in data.account_ids]
        try:
            items = await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=settings.overview_timeout
            )
        except TimeoutError as error:
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT, "Batch operation timed out"
            ) from error
        return OverviewResponse(
            requested=len(items),
            succeeded=sum(i.ok for i in items),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            items=list(items),
        )

    @router.get("/reports/interest-forecast", response_model=ForecastResponse, tags=["reports"])
    def interest_forecast(bank: ServiceDep) -> ForecastResponse:
        """Total funds in one year with daily capitalisation (NumPy, chosen in lab 9)."""
        accounts = bank.accounts.get_all()
        balances = np.array([a.balance_cents for a in accounts], dtype=np.int64)
        rates = np.array([RATE_BP[a.account_type] for a in accounts], dtype=np.int64)
        projected = project_balances(balances, rates)
        return ForecastResponse(
            accounts=len(accounts),
            total_now=from_cents(int(balances.sum())),
            total_in_one_year=from_cents(int(projected.sum())),
        )

    return router


app = create_app()
