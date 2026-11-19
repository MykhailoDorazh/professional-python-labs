"""Experiments of laboratory work 5 (python -m employee_io.experiments [1-6 ...])."""

import csv
import gc
import logging
import random
import re
import shutil
import sys
import traceback
import tracemalloc
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any

from employee_io.app import run_pipeline
from employee_io.config import load_config
from employee_io.exceptions import ApplicationError, DataExportError, RecordValidationError
from employee_io.exporters import export_json
from employee_io.logging_config import configure_logging
from employee_io.models import AppConfig, Employee
from employee_io.services import ImportStatistics, import_employees
from employee_io.validators import parse_employee

WORK = Path("experiments_tmp")
HEADER = ["employee_id", "name", "position", "department", "salary"]
DEPARTMENTS = ("IT", "Фінанси", "HR", "Продажі", "Логістика")


def generate_csv(path: Path, valid: int, invalid_lines: frozenset[int] = frozenset()) -> Path:
    """valid records + broken records at the given positions (1-based)."""
    rng = random.Random(6)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)
        total = valid + len(invalid_lines)
        for i in range(1, total + 1):
            row = [f"E{100_000 + i}", f"Працівник {i}", "Спеціаліст", rng.choice(DEPARTMENTS),
                   round(rng.uniform(20_000, 120_000), 2)]
            if i in invalid_lines:
                row[4] = "wrong"
            writer.writerow(row)
    return path


def base_config(input_path: Path, skip_invalid: bool) -> AppConfig:
    config = load_config(Path("config.yaml"), env={})
    out = WORK / "out"
    return replace(config, input_path=input_path, output_path=out / "employees.json",
                   errors_path=out / "errors.csv", summary_path=out / "summary.json",
                   processing=replace(config.processing, skip_invalid=skip_invalid))


# ---------------------------------------------------------------- 1
def experiment_strict_vs_tolerant() -> None:
    print("Експеримент 1. Strict vs tolerant: 1000 valid + 10 invalid records")
    path = generate_csv(WORK / "strict_tolerant.csv", 1000, frozenset(range(50, 1010, 100)))
    print(f"{'Параметр':<24}{'Strict':>14}{'Tolerant':>14}")
    results = {}
    for skip in (False, True):
        config = base_config(path, skip)
        try:
            stats, status = run_pipeline(config), "успішно (exit 0)"
        except ApplicationError as error:
            status = f"{type(error).__name__} (exit 1)"
            # для strict статистику відновлюємо повторним проходом до першої помилки
            stats = ImportStatistics()
            try:
                for _ in import_employees(config, stats):
                    pass
            except RecordValidationError:
                pass
        results[skip] = (stats, status)
    s, t = results[False][0], results[True][0]
    rows = [("Оброблено записів", s.total, t.total), ("Valid", s.valid, t.valid),
            ("Invalid", s.invalid, t.invalid), ("Exported", 0, t.exported)]
    for name, a, b in rows:
        print(f"{name:<24}{a:>14}{b:>14}")
    print(f"Завершення strict:   {results[False][1]}")
    print(f"Завершення tolerant: {results[True][1]}")


# ---------------------------------------------------------------- 2
def eager_import(path: Path, config: AppConfig) -> int:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    employees: list[Employee] = []
    for line, row in enumerate(rows, start=2):
        try:
            employee = parse_employee(row, line_number=line, config=config.processing)
        except RecordValidationError:
            continue
        if employee.salary >= config.processing.min_salary:
            employees.append(employee)
    return export_json(employees, config.output_path)


def streaming_import(path: Path, config: AppConfig) -> int:
    return export_json(import_employees(config, ImportStatistics()), config.output_path)


def measure(function: Callable[..., Any], *args: Any) -> tuple[float, int]:
    gc.collect()
    start = perf_counter()
    function(*args)
    elapsed = perf_counter() - start
    gc.collect()
    tracemalloc.start()
    function(*args)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return elapsed, peak


def experiment_streaming_vs_eager() -> None:
    print("Експеримент 2. Streaming vs eager (імпорт + валідація + фільтр + JSON export)")
    print(f"{'Records':>8} | {'Eager time':>10} | {'Stream time':>11} | "
          f"{'Eager peak RAM':>14} | {'Stream peak RAM':>15}")
    for size in (10_000, 100_000, 500_000):
        path = WORK / f"big_{size}.csv"
        if not path.exists():
            generate_csv(path, size)
        config = base_config(path, True)
        et, em = measure(eager_import, path, config)
        st, sm = measure(streaming_import, path, config)
        print(f"{size:>8} | {et:>8.2f} s | {st:>9.2f} s | {em / 2**20:>11.2f} MB | "
              f"{sm / 2**20:>12.2f} MB")


# ---------------------------------------------------------------- 3
def experiment_exception_chaining() -> None:
    print("Експеримент 3. Exception chaining: salary = 'wrong'")
    row = {"employee_id": "E100001", "name": "Іван Петренко", "position": "Розробник",
           "department": "IT", "salary": "wrong"}
    config = base_config(Path("data/employees.csv"), True)
    try:
        parse_employee(row, line_number=2, config=config.processing)
    except RecordValidationError as error:
        text = "".join(traceback.format_exception(error))
        lines = [ln for ln in text.splitlines()
                 if not ln.startswith("    ") and "~" not in ln and "^" not in ln]
        print("\n".join(lines))
        print(f"error.__cause__ = {error.__cause__!r}; line={error.line_number}, "
              f"field={error.field}")


# ---------------------------------------------------------------- 4
def failing_employees(count: int) -> Iterator[Employee]:
    for i in range(count):
        if i == 2:
            raise OSError("Disk is full (simulated)")
        yield Employee(f"E10000{i}", "Тест", "Тестувальник", "IT", 30_000.0)


def experiment_atomic_output() -> None:
    print("Експеримент 4. Atomic output: збій посеред export")
    output = WORK / "atomic" / "employees.json"
    export_json(iter([Employee("E100001", "Тест", "Тестувальник", "IT", 30_000.0)]), output)
    before = output.read_text(encoding="utf-8")
    try:
        export_json(failing_employees(5), output)
    except DataExportError as error:
        print(f"  DataExportError: {error}; cause: {error.__cause__!r}")
    print(f"  попередній output не змінився: {output.read_text(encoding='utf-8') == before}")
    print(f"  .tmp видалено: {not output.with_suffix('.json.tmp').exists()}")


# ---------------------------------------------------------------- 5
def experiment_configuration_errors() -> None:
    print("Експеримент 5. Configuration errors")
    folder = WORK / "configs"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy("data/employees.csv", folder / "employees.csv")
    good = Path("config.yaml").read_text(encoding="utf-8").replace(
        "data/employees.csv", "employees.csv")
    cases = {
        "1. відсутній config.yaml": None,
        "2. неправильний YAML": "input: [unclosed\n  path: x",
        "3. немає ключа input": good.replace("input:\n  path: employees.csv\n", ""),
        "4. min_salary = -5": good.replace("min_salary: 20000", "min_salary: -5"),
        "5. input file відсутній": good.replace("employees.csv", "missing.csv"),
        "6. output directory не існує": good.replace("output/", "new_dir/"),
        "7. порожні allowed_departments": good.replace(
            "[IT, Фінанси, HR, Продажі, Логістика]", "[]"),
        "8. min_salary > max_salary": good.replace("max_salary: 1000000", "max_salary: 1000"),
    }
    for name, text in cases.items():
        path = folder / f"case{name[0]}.yaml"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        try:
            config = load_config(path, env={})
            print(f"  {name:<32} OK, каталог створено: {config.output_path.parent.exists()}")
        except ApplicationError as error:
            cause = type(error.__cause__).__name__ if error.__cause__ else "-"
            print(f"  {name:<32} {type(error).__name__}: {error} (cause: {cause})")


# ---------------------------------------------------------------- 6
def experiment_log_privacy() -> None:
    print("Експеримент 6. Захист даних про зарплату в логах (рівень DEBUG)")
    log = WORK / "privacy.log"
    log.unlink(missing_ok=True)
    configure_logging("DEBUG", log, console=False)
    config = base_config(Path("data/employees.csv"), True)
    stats = run_pipeline(config)
    logging.shutdown()
    text = log.read_text(encoding="utf-8")
    with Path("data/employees.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    salaries = {r["salary"] for r in rows} | {f"{float(r['salary']):g}" for r in rows
                                              if re.fullmatch(r"-?[\d.]+", r["salary"])}
    names = {r["name"] for r in rows if r["name"]}
    leaked_salaries = sorted(s for s in salaries if re.search(rf"(?<![\d.]){re.escape(s)}(?![\d.])", text))
    leaked_names = sorted(n for n in names if n in text)
    print(f"  рядків у лозі: {len(text.splitlines())}, експортовано: {stats.exported}")
    print(f"  знайдено точних значень зарплати: {len(leaked_salaries)} {leaked_salaries}")
    print(f"  знайдено повних ПІБ: {len(leaked_names)} {leaked_names}")
    for line in text.splitlines():
        if "Accepted" in line or "Filtered" in line:
            print("  ", line.split(" | ", 3)[3])
            break
    for line in text.splitlines():
        if "Filtered" in line:
            print("  ", line.split(" | ", 3)[3])
            break


EXPERIMENTS = {"1": experiment_strict_vs_tolerant, "2": experiment_streaming_vs_eager,
               "3": experiment_exception_chaining, "4": experiment_atomic_output,
               "5": experiment_configuration_errors, "6": experiment_log_privacy}


def main() -> None:
    WORK.mkdir(exist_ok=True)
    for key in sys.argv[1:] or list(EXPERIMENTS):
        configure_logging("WARNING", WORK / "experiments.log", console=False)
        logging.getLogger().setLevel(logging.ERROR)
        EXPERIMENTS[key]()
        print()


if __name__ == "__main__":
    main()
