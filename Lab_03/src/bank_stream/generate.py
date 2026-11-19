"""Test data set generator (python -m bank_stream.generate N [N ...])."""

import csv
import random
import sys
from collections.abc import Iterator
from pathlib import Path

from bank_stream.utils import account_numbers

FIRST_NAMES = ("Іван", "Олена", "Андрій", "Марія", "Олег", "Наталія", "Тарас",
               "Софія", "Петро", "Ірина", "Богдан", "Юлія")
LAST_NAMES = ("Петренко", "Коваль", "Мельник", "Бондар", "Шевченко", "Гнатюк",
              "Новак", "Лисенко", "Ткачук", "Кравець", "Савчук", "Олійник")
HEADER = ["account_number", "client", "balance", "operation", "amount"]


def generate_rows(count: int, seed: int = 4, invalid_ratio: float = 0.02) -> Iterator[list]:
    """Lazily produce `count` rows; about `invalid_ratio` of them are broken."""
    rng = random.Random(seed)
    numbers = account_numbers()
    for _ in range(count):
        row = [
            next(numbers),
            f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            round(rng.uniform(0, 100_000), 2),
            rng.choice(("deposit", "withdraw")),
            round(rng.uniform(1, 20_000), 2),
        ]
        if rng.random() < invalid_ratio:
            field, bad = rng.choice((
                (0, "UA12AB"), (1, ""), (2, "-150.00"),
                (3, "transfer"), (4, "abc"), (4, "-20"),
            ))
            row[field] = bad
        yield row


def generate_file(path: Path, count: int, seed: int = 4) -> Path:
    """Write the data set row by row (streaming export)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)
        writer.writerows(generate_rows(count, seed))
    return path


def dataset_path(count: int) -> Path:
    return Path("data") / f"operations_{count}.csv"


def main() -> None:
    sizes = [int(arg) for arg in sys.argv[1:]] or [100_000]
    for size in sizes:
        path = generate_file(dataset_path(size), size)
        print(f"{path.as_posix()}: {size} records, {path.stat().st_size / 2**20:.1f} MB")


if __name__ == "__main__":
    main()
