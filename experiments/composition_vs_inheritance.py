"""Experiment: the same behavior (import of employees from text lines) built
with inheritance (BaseProcessor -> CsvProcessor) and with composition
(Processor has Parser, Validator, Formatter)."""

import json
from abc import ABC, abstractmethod
from typing import Protocol

LINES = ["E0001;Олена Коваль;IT;95000", "E1;Іван Петренко;IT;72000", "E0003;Тарас Новак;HR;-5"]
Row = dict[str, str | float]


# ---------------- Inheritance ----------------
class BaseProcessor(ABC):
    def process(self, lines: list[str]) -> list[str]:
        rows = [self.parse(line) for line in lines]
        return [self.format(row) for row in rows if self.is_valid(row)]

    @abstractmethod
    def parse(self, line: str) -> Row: ...

    def is_valid(self, row: Row) -> bool:
        return len(str(row["id"])) == 5 and float(row["salary"]) >= 0

    def format(self, row: Row) -> str:
        return f"{row['id']} {row['name']} {row['department']} {row['salary']}"


class CsvProcessor(BaseProcessor):
    def parse(self, line: str) -> Row:
        employee_id, name, department, salary = line.split(";")
        return {"id": employee_id, "name": name, "department": department,
                "salary": float(salary)}


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
    employee_id, name, department, salary = line.split(";")
    return {"id": employee_id, "name": name, "department": department, "salary": float(salary)}


def employee_validator(row: Row) -> bool:
    return len(str(row["id"])) == 5 and float(row["salary"]) >= 0


def text_formatter(row: Row) -> str:
    return f"{row['id']} {row['name']} {row['department']} {row['salary']}"


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
          Processor(semicolon_parser, employee_validator, text_formatter).process(LINES))
    print("Composition, json formatter:    ",
          Processor(semicolon_parser, employee_validator, json_formatter).process(LINES))
    print("Composition, validator замінено:",
          Processor(semicolon_parser, lambda row: True, text_formatter).process(LINES))


if __name__ == "__main__":
    main()
