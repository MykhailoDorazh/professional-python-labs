"""Use case: import -> validation -> processing -> atomic export."""

import logging

from bank_io.exporters import export_errors_csv, export_json, export_summary
from bank_io.models import AppConfig
from bank_io.services import ImportStatistics, import_operations
from bank_io.utils import logged_operation

logger = logging.getLogger(__name__)


def run_pipeline(config: AppConfig) -> ImportStatistics:
    statistics = ImportStatistics()
    mode = "tolerant" if config.processing.skip_invalid else "strict"
    with logged_operation(f"Import/export ({mode} mode)"):
        operations = import_operations(config, statistics)
        statistics.exported = export_json(operations, config.output_path)
        export_errors_csv(statistics.errors, config.errors_path)
        export_summary(statistics.to_dict(), config.summary_path)
    logger.info("Total=%s, valid=%s, invalid=%s, exported=%s", statistics.total,
                statistics.valid, statistics.invalid, statistics.exported)
    return statistics
