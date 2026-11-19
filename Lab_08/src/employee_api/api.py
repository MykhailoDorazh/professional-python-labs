"""FastAPI REST API of the employee system: HTTP + JSON over Service and Repository layers."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from employee_api import __version__
from employee_api.database import DATABASE_URL, init_db, make_engine, make_session_factory
from employee_api.exceptions import (
    DepartmentNotEmptyError,
    DepartmentNotFoundError,
    DuplicateDepartmentError,
    DuplicateEmployeeError,
    EmployeeNotFoundError,
    HRError,
    InvalidSalaryError,
)
from employee_api.models import Department, Employee
from employee_api.money import to_cents
from employee_api.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentStatistics,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    ErrorResponse,
    RaiseResponse,
    SalaryRaise,
    StatisticsBatchItem,
    StatisticsBatchRequest,
    StatisticsBatchResponse,
    SummaryResponse,
)
from employee_api.services import HRService

ERROR_STATUS: dict[type[HRError], int] = {
    EmployeeNotFoundError: status.HTTP_404_NOT_FOUND,
    DepartmentNotFoundError: status.HTTP_404_NOT_FOUND,
    DuplicateEmployeeError: status.HTTP_409_CONFLICT,
    DuplicateDepartmentError: status.HTTP_409_CONFLICT,
    DepartmentNotEmptyError: status.HTTP_409_CONFLICT,
    InvalidSalaryError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}
ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Ресурс не знайдено"},
    409: {"model": ErrorResponse, "description": "Конфлікт із бізнес-правилами"},
}
STATS_CONCURRENCY = 4  # at most 4 DB reads at the same time
STATS_TIMEOUT = 5.0  # seconds for the whole batch


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
        title="Employee Management API",
        version=__version__,
        description="REST API обліку працівників (ЛР №8, варіант 6).",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "employees", "description": "Працівники: CRUD, пошук, фільтрація"},
            {"name": "departments", "description": "Відділи, працівники відділу, статистика"},
            {"name": "reports", "description": "Підсумки та асинхронна агрегація"},
        ],
    )

    @app.exception_handler(HRError)
    async def hr_error_handler(_: Request, error: HRError) -> JSONResponse:
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


def get_service(session: Annotated[Session, Depends(get_session)]) -> HRService:
    return HRService(session)


ServiceDep = Annotated[HRService, Depends(get_service)]


def build_router() -> APIRouter:
    router = APIRouter()

    # ---------- meta ----------
    @router.get("/", tags=["reports"])
    async def root() -> dict[str, str]:
        return {"message": "Employee Management API is running", "docs": "/docs"}

    @router.get("/health", tags=["reports"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    # ---------- employees ----------
    @router.get("/employees", response_model=list[EmployeeResponse], tags=["employees"])
    def list_employees(
        hr: ServiceDep,
        department_id: Annotated[int | None, Query(gt=0)] = None,
        position: Annotated[str | None, Query(description="Точна назва посади")] = None,
        search: Annotated[str | None, Query(min_length=2, description="Частина ПІБ або посади")] = None,
        min_salary: Annotated[Decimal | None, Query(ge=0)] = None,
        max_salary: Annotated[Decimal | None, Query(ge=0)] = None,
        sort_by_salary: bool = False,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Employee]:
        if search is not None:
            employees = hr.employees.search(search)
            if sort_by_salary:
                employees.sort(key=lambda e: e.salary_cents, reverse=True)
        else:
            employees = hr.employees.filter(
                min_salary_cents=None if min_salary is None else to_cents(min_salary),
                position=position, order_by_salary=sort_by_salary)
        if department_id is not None:
            employees = [e for e in employees if e.department_id == department_id]
        if search is not None and position is not None:
            employees = [e for e in employees if e.position == position]
        if search is not None and min_salary is not None:
            employees = [e for e in employees if e.salary_cents >= to_cents(min_salary)]
        if max_salary is not None:
            employees = [e for e in employees if e.salary_cents <= to_cents(max_salary)]
        return employees[offset:offset + limit]

    @router.get("/employees/{employee_id}", response_model=EmployeeResponse,
                tags=["employees"], responses=ERRORS)
    def get_employee(employee_id: int, hr: ServiceDep) -> Employee:
        return hr.get_employee_by_id(employee_id)

    @router.post("/employees", response_model=EmployeeResponse,
                 status_code=status.HTTP_201_CREATED, tags=["employees"], responses=ERRORS)
    def create_employee(data: EmployeeCreate, hr: ServiceDep) -> Employee:
        department = hr.get_department_by_id(data.department_id)  # 404 instead of FK error
        return hr.hire(data.personnel_number, data.full_name, data.position, data.salary,
                       department.code, data.hire_date)

    @router.patch("/employees/{employee_id}", response_model=EmployeeResponse,
                  tags=["employees"], responses=ERRORS)
    def update_employee(employee_id: int, data: EmployeeUpdate, hr: ServiceDep) -> Employee:
        return hr.update_employee(employee_id, **data.model_dump(exclude_unset=True))

    @router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT,
                   tags=["employees"], responses=ERRORS)
    def delete_employee(employee_id: int, hr: ServiceDep) -> None:
        hr.fire(hr.get_employee_by_id(employee_id).personnel_number)

    # ---------- departments ----------
    @router.get("/departments", response_model=list[DepartmentResponse], tags=["departments"])
    def list_departments(hr: ServiceDep) -> list[Department]:
        return hr.list_departments()

    @router.post("/departments", response_model=DepartmentResponse,
                 status_code=status.HTTP_201_CREATED, tags=["departments"], responses=ERRORS)
    def create_department(data: DepartmentCreate, hr: ServiceDep) -> Department:
        return hr.create_department(data.code, data.name)

    @router.get("/departments/{department_id}", response_model=DepartmentResponse,
                tags=["departments"], responses=ERRORS)
    def get_department(department_id: int, hr: ServiceDep) -> Department:
        return hr.get_department_by_id(department_id)

    @router.get("/departments/{department_id}/employees",
                response_model=list[EmployeeResponse], tags=["departments"], responses=ERRORS)
    def department_employees(department_id: int, hr: ServiceDep) -> list[Employee]:
        return hr.employees_in(hr.get_department_by_id(department_id).code)

    @router.get("/departments/{department_id}/statistics", response_model=DepartmentStatistics,
                tags=["departments"], responses=ERRORS)
    def department_statistics(department_id: int, hr: ServiceDep) -> dict[str, object]:
        return hr.department_statistics(department_id)

    @router.post("/departments/{department_id}/raise", response_model=RaiseResponse,
                 tags=["departments"], responses=ERRORS)
    def raise_salaries(department_id: int, data: SalaryRaise, hr: ServiceDep) -> RaiseResponse:
        """Mass salary change in one transaction: all salaries or none."""
        department = hr.get_department_by_id(department_id)
        updated = hr.raise_salaries(department.code, data.percent)
        return RaiseResponse(department_id=department_id, updated=updated,
                             payroll=hr.payroll(department.code))

    # ---------- reports ----------
    @router.get("/stats", response_model=SummaryResponse, tags=["reports"])
    def summary(hr: ServiceDep) -> SummaryResponse:
        return SummaryResponse(departments=hr.departments.count(),
                               employees=hr.employees.count(),
                               payroll=hr.payroll(), average_salary=hr.average_salary())

    @router.post("/departments/statistics", response_model=StatisticsBatchResponse,
                 tags=["reports"])
    async def statistics_batch(data: StatisticsBatchRequest,
                               request: Request) -> StatisticsBatchResponse:
        """Statistics of several departments, loaded concurrently.

        Every department is read by its own asyncio.Task in a worker thread with its own
        session; a Semaphore limits parallel DB reads, wait_for limits total time.
        """
        factory: sessionmaker[Session] = request.app.state.session_factory
        semaphore = asyncio.Semaphore(STATS_CONCURRENCY)
        started = time.perf_counter()

        def load(department_id: int) -> StatisticsBatchItem:
            with factory() as session:
                try:
                    stats = HRService(session).department_statistics(department_id)
                except DepartmentNotFoundError as error:
                    return StatisticsBatchItem(department_id=department_id, ok=False,
                                               error=str(error))
                return StatisticsBatchItem(department_id=department_id, ok=True,
                                           statistics=DepartmentStatistics.model_validate(stats))

        async def load_limited(department_id: int) -> StatisticsBatchItem:
            async with semaphore:
                return await asyncio.to_thread(load, department_id)

        tasks = [asyncio.create_task(load_limited(i)) for i in data.department_ids]
        try:
            items = await asyncio.wait_for(asyncio.gather(*tasks), timeout=STATS_TIMEOUT)
        except TimeoutError as error:
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT,
                                "Batch operation timed out") from error
        return StatisticsBatchResponse(
            requested=len(items), succeeded=sum(i.ok for i in items),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2), items=list(items),
        )

    return router


app = create_app()
