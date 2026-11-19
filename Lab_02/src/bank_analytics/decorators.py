"""Decorators: execution time measurement and operation history."""

from collections import deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any

# deque з обмеженою довжиною: зберігає лише 5 останніх операцій,
# старі записи автоматично витісняються з лівого кінця за O(1).
OPERATION_HISTORY: deque[str] = deque(maxlen=5)


def measure_time(func: Callable) -> Callable:
    """Print how long the decorated function was running."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        print(f"  [time] {func.__name__}: {elapsed * 1e6:.1f} мкс")
        return result

    return wrapper


def log_operation(
    label: str,
    history: deque[str] = OPERATION_HISTORY,
) -> Callable[[Callable], Callable]:
    """Parameterized decorator: writes the operation into the history.

    `label` and `history` are remembered by a closure.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            history.append(f"{label} ({func.__name__})")
            return result

        return wrapper

    return decorator
