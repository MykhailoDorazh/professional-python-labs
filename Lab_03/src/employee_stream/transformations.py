"""Transformation stage: normalisation of names and departments in the stream."""

from collections.abc import Iterable, Iterator

from employee_stream.models import Employee


def normalize(employees: Iterable[Employee]) -> Iterator[Employee]:
    """'іВАН  петренко' -> 'Іван Петренко'; extra spaces in department removed."""
    for employee in employees:
        yield employee._replace(
            name=" ".join(employee.name.split()).title(),
            department=" ".join(employee.department.split()),
            salary=round(employee.salary, 2),
        )


def short_view(employees: Iterable[Employee]) -> Iterator[str]:
    """Lazy transformation into a short text representation."""
    return (
        f"{e.employee_id} {e.name:<16} {e.position:<12} {e.department:<10} {e.salary:>10.2f}"
        for e in employees
    )
