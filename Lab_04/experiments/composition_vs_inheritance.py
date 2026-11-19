"""Experiment: the same behavior (import of accounts from text lines) built
with inheritance (BaseProcessor -> CsvProcessor) and with composition
(Processor has Parser, Validator, Formatter)."""

import json
from abc import ABC, abstractmethod
from typing import Protocol

LINES = ["UA100001;Іван Петренко;50000", "UA1;Олена Коваль;10", "UA100003;Тарас Новак;-5"]
Row = dict[str, str | float]


# ---------------- Inheritance ----------------
class BaseProcessor(ABC):
    def process(self, lines: list[str]) -> list[str]:
        rows = [self.parse(line) for line in lines]
        return [self.format(row) for row in rows if self.is_valid(row)]

    @abstractmethod
    def parse(self, line: str) -> Row: ...

    def is_valid(self, row: Row) -> bool:
        return len(str(row["number"])) == 8 and float(row["balance"]) >= 0

    def format(self, row: Row) -> str:
        return f"{row['number']} {row['client']} {row['balance']}"


class CsvProcessor(BaseProcessor):
    def parse(self, line: str) -> Row:
        number, client, balance = line.split(";")
        return {"number": number, "client": client, "balance": float(balance)}


class CsvJsonProcessor(CsvProcessor):  # новий формат виводу = ще один підклас
    def format(self, row: Row) -> str:
        return json.dumps(row, ensure_ascii=False)


# ---------------- Composition ----------------
class Parser(Protocol):
    def __call__(self, line: str) -> Row: ...


class Validator(Protocol):
    def __call__(self, row: Row) -> bool: ...


class Formatter(Protocol):
    def __call__(self, row: Row) -> str: ...


def semicolon_parser(line: str) -> Row:
    number, client, balance = line.split(";")
    return {"number": number, "client": client, "balance": float(balance)}


def account_validator(row: Row) -> bool:
    return len(str(row["number"])) == 8 and float(row["balance"]) >= 0


def text_formatter(row: Row) -> str:
    return f"{row['number']} {row['client']} {row['balance']}"


def json_formatter(row: Row) -> str:
    return json.dumps(row, ensure_ascii=False)


class Processor:
    def __init__(self, parser: Parser, validator: Validator, formatter: Formatter) -> None:
        self.parser, self.validator, self.formatter = parser, validator, formatter

    def process(self, lines: list[str]) -> list[str]:
        rows = (self.parser(line) for line in lines)
        return [self.formatter(row) for row in rows if self.validator(row)]


def main() -> None:
    print("Inheritance, CsvProcessor:      ", CsvProcessor().process(LINES))
    print("Inheritance, CsvJsonProcessor:  ", CsvJsonProcessor().process(LINES))
    print("Composition, text formatter:    ",
          Processor(semicolon_parser, account_validator, text_formatter).process(LINES))
    print("Composition, json formatter:    ",
          Processor(semicolon_parser, account_validator, json_formatter).process(LINES))
    print("Composition, validator замінено:",
          Processor(semicolon_parser, lambda row: True, text_formatter).process(LINES))


if __name__ == "__main__":
    main()
