"""SQLAlchemy ORM models: departments 1─N employees."""

from __future__ import annotations

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # passive_deletes="all": ORM не обнуляє department_id, видалення відділу з
    # працівниками блокує сама БД (FOREIGN KEY ... ON DELETE RESTRICT)
    employees: Mapped[list[Employee]] = relationship(
        back_populates="department", order_by="Employee.personnel_number",
        passive_deletes="all",
    )

    def __repr__(self) -> str:
        return f"Department(code={self.code!r}, name={self.name!r})"


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "salary_cents >= 0 AND salary_cents <= 100000000",
            name="ck_employees_salary_range",
        ),
        CheckConstraint("length(trim(full_name)) > 0", name="ck_employees_name_not_empty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    personnel_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    salary_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Added by migration 0002_add_hire_date.
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    department: Mapped[Department] = relationship(back_populates="employees")

    def __repr__(self) -> str:
        return (f"Employee(personnel_number={self.personnel_number!r}, "
                f"salary_cents={self.salary_cents})")
