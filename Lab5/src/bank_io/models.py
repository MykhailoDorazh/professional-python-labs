"""Domain records and configuration models."""

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Operation:
    """Validated operation already applied to the account."""

    account_number: str
    client: str
    operation: str
    amount: float
    balance_before: float
    balance_after: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    skip_invalid: bool
    allowed_operations: tuple[str, ...]
    currency: str
    max_amount: float


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
