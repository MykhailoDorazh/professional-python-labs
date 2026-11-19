"""Test data set generator (python -m employee_stream.generate N [N ...])."""

import csv
import random
import sys
from collections.abc import Iterator
from pathlib import Path

from employee_stream.utils import employee_ids

FIRST_NAMES = ("Іван", "Олена", "Андрій", "Марія", "Олег", "Наталія", "Тарас",
               "Софія", "Петро", "Ірина", "Богдан", "Юлія")
LAST_NAMES = ("Петренко", "Коваль", "Мельник", "Бондар", "Шевченко", "Гнатюк",
              "Новак", "Лисенко", "Ткачук", "Кравець", "Савчук", "Олійник")
POSITIONS = {
    "IT": ("Розробник", "Тестувальник", "Тімлід", "DevOps"),
    "Фінанси": ("Бухгалтер", "Аналітик", "Економіст"),
    "HR": ("Рекрутер", "HR-менеджер"),
    "Продажі": ("Менеджер", "Консультант"),
    "Логістика": ("Логіст", "Комірник", "Водій"),
}
SALARY_RANGE = {"IT": (35_000, 120_000), "Фінанси": (25_000, 80_000), "HR": (22_000, 55_000),
                "Продажі": (18_000, 60_000), "Логістика": (16_000, 45_000)}
HEADER = ["employee_id", "name", "position", "department", "salary"]


def generate_rows(count: int, seed: int = 6, invalid_ratio: float = 0.02) -> Iterator[list]:
    """Lazily produce `count` rows; about `invalid_ratio` of them are broken."""
    rng = random.Random(seed)
    ids = employee_ids()
    for _ in range(count):
        department = rng.choice(tuple(POSITIONS))
        low, high = SALARY_RANGE[department]
        row = [
            next(ids),
            f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            rng.choice(POSITIONS[department]),
            department,
            round(rng.uniform(low, high), 2),
        ]
        if rng.random() < invalid_ratio:
            field, bad = rng.choice((
                (0, "E12AB"), (1, ""), (2, ""), (3, " "),
                (4, "-1500.00"), (4, "abc"), (4, "5000000"),
            ))
            row[field] = bad
        yield row


def generate_file(path: Path, count: int, seed: int = 6) -> Path:
    """Write the data set row by row (streaming export)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)
        writer.writerows(generate_rows(count, seed))
    return path


def dataset_path(count: int) -> Path:
    return Path("data") / f"employees_{count}.csv"


def main() -> None:
    sizes = [int(arg) for arg in sys.argv[1:]] or [100_000]
    for size in sizes:
        path = generate_file(dataset_path(size), size)
        print(f"{path.as_posix()}: {size} records, {path.stat().st_size / 2**20:.1f} MB")


if __name__ == "__main__":
    main()
