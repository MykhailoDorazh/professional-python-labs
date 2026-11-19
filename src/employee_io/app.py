"""Use case: import -> validation -> salary filter -> atomic export."""

import logging

from employee_io.exporters import export_errors_csv, export_json, export_summary
from employee_io.models import AppConfig
from employee_io.services import ImportStatistics, import_employees
from employee_io.utils import logged_operation

logger = logging.getLogger(__name__)


def run_pipeline(config: AppConfig) -> ImportStatistics:
    statistics = ImportStatistics()
    mode = "tolerant" if config.processing.skip_invalid else "strict"
    with logged_operation(f"Import/export ({mode} mode)"):
        employees = import_employees(config, statistics)
        statistics.exported = export_json(employees, config.output_path)
        export_errors_csv(statistics.errors, config.errors_path)
        export_summary(statistics.to_dict(), config.summary_path)
    # агреговані показники без персональних даних
    logger.info("Total=%s, valid=%s, invalid=%s, filtered=%s, exported=%s", statistics.total,
                statistics.valid, statistics.invalid, statistics.filtered, statistics.exported)
    return statistics
