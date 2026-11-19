"""Domain records and configuration models."""

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Employee:
    """Validated employee record."""

    employee_id: str
    name: str
    position: str
    department: str
    salary: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    skip_invalid: bool
    allowed_departments: tuple[str, ...]
    min_salary: float
    max_salary: float
    currency: str


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str
    path: Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    input_path: Path
    output_path: Path
    errors_path: Path
    summary_path: Path
    processing: ProcessingConfig
    logging: LoggingConfig
