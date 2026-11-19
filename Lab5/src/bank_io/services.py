"""Import service: strict/tolerant processing and statistics."""

import logging
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field

from bank_io.exceptions import RecordValidationError
from bank_io.models import AppConfig, Operation
from bank_io.readers import get_importer
from bank_io.utils import mask_account
from bank_io.validators import parse_operation

logger = logging.getLogger(__name__)


@dataclass
class ImportStatistics:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    exported: int = 0
    deposits: float = 0.0
    withdrawals: float = 0.0
    total_funds: float = 0.0
    reasons: Counter[str] = field(default_factory=Counter)
    errors: list[tuple[int, str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total, "valid": self.valid, "invalid": self.invalid,
            "exported": self.exported, "deposits": round(self.deposits, 2),
            "withdrawals": round(self.withdrawals, 2),
            "total_funds": round(self.total_funds, 2), "invalid_by_field": dict(self.reasons),
        }


def import_operations(config: AppConfig, statistics: ImportStatistics) -> Iterator[Operation]:
    """Streaming import: valid operations are produced one by one.

    Tolerant mode (skip_invalid=true): invalid record -> warning, counter, skip.
    Strict mode (skip_invalid=false): the first invalid record stops the import.
    """
    importer = get_importer(config.input_path)
    for line_number, row in importer.read(config.input_path):
        statistics.total += 1
        try:
            operation = parse_operation(row, line_number=line_number,
                                        config=config.processing)
        except RecordValidationError as error:
            statistics.invalid += 1
            statistics.reasons[error.field or "unknown"] += 1
            statistics.errors.append((line_number, error.field or "", str(error)))
            logger.warning("Invalid record at line %s (%s): %s [field=%s]", line_number,
                           mask_account(row.get("account_number") or ""), error, error.field)
            if config.processing.skip_invalid:
                continue
            raise
        statistics.valid += 1
        statistics.total_funds += operation.balance_after
        if operation.operation == "deposit":
            statistics.deposits += operation.amount
        else:
            statistics.withdrawals += operation.amount
        yield operation
