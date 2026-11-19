"""Pydantic schemas: validation of requests and serialization of responses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from employee_api.money import from_cents

Salary = Annotated[Decimal, Field(ge=0, le=1_000_000, max_digits=9, decimal_places=2,
                                  examples=["52000.00"])]
PersonnelNumber = Annotated[
    str, Field(pattern=r"^E\d{4}$", examples=["E0007"], description="E + 4 цифри")
]
Text = Annotated[str, Field(min_length=2, max_length=100)]


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.strip():
        raise ValueError("значення не може складатися з пробілів")
    return " ".join(value.split())


# ---------- requests ----------
class DepartmentCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z]{2,10}$", examples=["SALES"])
    name: Text = Field(examples=["Продажі"])

    _strip_name = field_validator("name")(_strip)


class EmployeeCreate(BaseModel):
    personnel_number: PersonnelNumber
    full_name: Text = Field(examples=["Олена Коваль"])
    position: Text = Field(examples=["Python-розробник"])
    salary: Salary
    department_id: int = Field(gt=0)
    hire_date: date | None = None

    _strip_text = field_validator("full_name", "position")(_strip)


class EmployeeUpdate(BaseModel):
    """PATCH body: every field is optional, only sent fields are changed."""

    full_name: Text | None = None
    position: Text | None = None
    salary: Salary | None = None
    department_id: int | None = Field(default=None, gt=0)
    hire_date: date | None = None

    _strip_text = field_validator("full_name", "position")(_strip)


class SalaryRaise(BaseModel):
    percent: Decimal = Field(gt=-100, le=1000, max_digits=6, decimal_places=2, examples=["10"])


class StatisticsBatchRequest(BaseModel):
    department_ids: list[int] = Field(min_length=1, max_length=50)


# ---------- responses ----------
class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    personnel_number: str
    full_name: str
    position: str
    department_id: int
    hire_date: date | None
    salary_cents: int = Field(exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def salary(self) -> Decimal:
        return from_cents(self.salary_cents)


class DepartmentStatistics(BaseModel):
    department_id: int
    code: str
    name: str
    employees: int
    payroll: Decimal
    average_salary: Decimal
    min_salary: Decimal
    max_salary: Decimal
    highest_paid: str | None


class StatisticsBatchItem(BaseModel):
    department_id: int
    ok: bool
    statistics: DepartmentStatistics | None = None
    error: str | None = None


class StatisticsBatchResponse(BaseModel):
    requested: int
    succeeded: int
    elapsed_ms: float
    items: list[StatisticsBatchItem]


class RaiseResponse(BaseModel):
    department_id: int
    updated: int
    payroll: Decimal


class SummaryResponse(BaseModel):
    departments: int
    employees: int
    payroll: Decimal
    average_salary: Decimal


class ErrorResponse(BaseModel):
    error: str
    detail: str
