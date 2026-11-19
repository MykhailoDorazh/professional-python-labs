"""Demonstration of the persistence layer: CRUD, transactions, reports, DB-API."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import date
from pathlib import Path

from employee_db.database import init_db, make_engine, make_session_factory
from employee_db.dbapi import find_by_department
from employee_db.exceptions import HRError
from employee_db.money import fmt
from employee_db.services import HRService


def print_employees(hr: HRService) -> None:
    print(f"  {'Номер':<7}{'ПІБ':<17}{'Посада':<20}{'Відділ':<7}{'Зарплата':>12}")
    for e in hr.list_employees():
        print(f"  {e.personnel_number:<7}{e.full_name:<17}{e.position:<20}"
              f"{e.department.code:<7}{fmt(e.salary_cents):>12}")


def attempt(title: str, action: Callable[[], object]) -> None:
    try:
        action()
        print(f"  [OK]    {title}")
    except HRError as error:
        print(f"  [ERROR] {title}: {type(error).__name__}: {error}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Employee persistence layer demo")
    parser.add_argument("--db", default="demo.db", help="SQLite file for the demo")
    parser.add_argument("--echo", action="store_true", help="print SQL of the mass raise")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    db_path.unlink(missing_ok=True)
    engine = make_engine(f"sqlite:///{db_path}")
    init_db(engine)
    Session = make_session_factory(engine)

    with Session() as session:
        hr = HRService(session)
        print("== 1. Create: відділи і працівники ==")
        for code, name in (("IT", "Інформаційні технології"), ("FIN", "Фінанси"),
                           ("HR", "Персонал"), ("LOG", "Логістика")):
            hr.create_department(code, name)
        hr.hire("E0001", "Олена Коваль", "Керівник розробки", "95000", "IT", date(2021, 3, 1))
        hr.hire("E0002", "Іван Петренко", "Python-розробник", "72000", "IT", date(2023, 9, 4))
        hr.hire("E0003", "Тарас Новак", "Розробник", "41500", "IT")
        hr.hire("E0004", "Андрій Мельник", "Бухгалтер", "36800.50", "FIN")
        hr.hire("E0005", "Марія Бондар", "HR-менеджер", "48000", "HR")
        hr.hire("E0006", "Софія Лисенко", "Економіст", "39900", "FIN")
        print_employees(hr)

        print("\n== 2. Update: посада, зарплата, помилки ==")
        attempt("E0003 -> посада «Python-розробник»",
                lambda: hr.change_position("E0003", "Python-розробник"))
        attempt("E0003 -> зарплата 45 000", lambda: hr.change_salary("E0003", "45000"))
        attempt("E0004 -> зарплата -100", lambda: hr.change_salary("E0004", "-100"))
        attempt("E0004 -> зарплата 2 000 000", lambda: hr.change_salary("E0004", "2000000"))
        attempt("дублікат E0001", lambda: hr.hire("E0001", "Дублікат", "Тест", "1", "IT"))
        attempt("найм у відділ SALES", lambda: hr.hire("E0007", "Петро Ткачук", "Менеджер",
                                                         "30000", "SALES"))

        print("\n== 3. Переведення між відділами: COMMIT і ROLLBACK ==")
        attempt("E0005 -> FIN", lambda: hr.transfer("E0005", "FIN"))
        attempt("масово E0004, E0006 -> LOG", lambda: hr.transfer_many(["E0004", "E0006"], "LOG"))
        attempt("масово E0001, E0009 -> LOG",
                lambda: hr.transfer_many(["E0001", "E0009"], "LOG"))
        print(f"  E0001 після ROLLBACK залишився у відділі: {hr.get_employee('E0001').department.code}")

        print("\n== 4. Масова зміна зарплат: COMMIT і ROLLBACK ==")
        engine.echo = args.echo
        attempt("IT +10 %", lambda: hr.raise_salaries("IT", "10"))
        engine.echo = False
        before = hr.payroll("IT")
        attempt("IT +1000 % (E0001 > 1 000 000)", lambda: hr.raise_salaries("IT", "1000"))
        print(f"  Фонд IT до: {before}, після ROLLBACK: {hr.payroll('IT')}")
        print_employees(hr)

        print("\n== 5. Read: пошук за відділом і за текстом ==")
        print("  IT:", [e.personnel_number for e in hr.employees_in("it")])
        print("  LOG:", [e.personnel_number for e in hr.employees_in("LOG")])
        print("  пошук «розроб»:", [e.full_name for e in hr.employees.search("розроб")])
        print("  зарплата >= 50 000:", [e.personnel_number for e in
                                      hr.employees.filter(min_salary_cents=5_000_000,
                                                          order_by_salary=True)])

        print("\n== 6. Звіти (SUM / AVG / MAX / COUNT / GROUP BY / JOIN) ==")
        print(f"  Фонд оплати праці: {hr.payroll()} грн, середня: {hr.average_salary()} грн")
        top = hr.highest_paid()
        if top is not None:
            print(f"  Максимальна зарплата: {top.full_name} {fmt(top.salary_cents)} грн")
        print(f"  Середня в IT: {hr.average_salary('IT')} грн, фонд FIN: {hr.payroll('FIN')} грн")
        for code, name, count, total, avg, best in hr.department_stats():
            print(f"  {code:<4}{name:<25} осіб: {count}  фонд: {total:>10}  "
                  f"середня: {avg:>9}  max: {best:>9}")

        print("\n== 7. Delete: звільнення і видалення відділу ==")
        attempt("видалити відділ IT (є працівники)", lambda: hr.delete_department("IT"))
        attempt("звільнити E0005", lambda: hr.fire("E0005"))
        attempt("видалити порожній відділ HR", lambda: hr.delete_department("HR"))
        print(f"  Працівників: {hr.employees.count()}, відділів: {hr.departments.count()}")

    print("\n== 8. DB-API (sqlite3), parameterized query ==")
    for row in find_by_department(db_path, "IT"):
        print(" ", row)
    print("  injection \"' OR '1'='1\":", find_by_department(db_path, "' OR '1'='1"))
    engine.dispose()


if __name__ == "__main__":
    main()
