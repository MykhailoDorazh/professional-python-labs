"""Configuration constants of the application."""

CURRENCY: str = "грн"

# Зарплата не може бути від'ємною.
MIN_SALARY: float = 0.0

# Верхня межа зарплати (захист від помилок введення, наприклад зайвого нуля).
MAX_SALARY: float = 1_000_000.0

# Табельний номер працівника: "E" + 4 цифри, наприклад E1001.
EMPLOYEE_ID_PATTERN: str = r"E\d{4}"
