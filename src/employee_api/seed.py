"""Demo data for the API: five departments, ten employees."""

from __future__ import annotations

from datetime import date

from employee_api.database import init_db, make_engine, make_session_factory
from employee_api.services import HRService

DEPARTMENTS = (("IT", "Інформаційні технології"), ("FIN", "Фінанси"), ("HR", "Персонал"),
               ("LOG", "Логістика"), ("SALES", "Продажі"))
EMPLOYEES = (
    ("E0001", "Олена Коваль", "Керівник розробки", "95000", "IT", date(2021, 3, 1)),
    ("E0002", "Іван Петренко", "Python-розробник", "72000", "IT", date(2023, 9, 4)),
    ("E0003", "Тарас Новак", "Розробник", "41500", "IT", None),
    ("E0004", "Андрій Мельник", "Бухгалтер", "36800.50", "FIN", date(2020, 1, 15)),
    ("E0005", "Софія Лисенко", "Економіст", "39900", "FIN", None),
    ("E0006", "Марія Бондар", "HR-менеджер", "48000", "HR", date(2022, 6, 1)),
    ("E0007", "Петро Ткачук", "Логіст", "33000", "LOG", None),
    ("E0008", "Ірина Кравець", "Водій-експедитор", "28500", "LOG", None),
    ("E0009", "Богдан Савчук", "Менеджер з продажу", "45000", "SALES", None),
    ("E0010", "Юлія Олійник", "Керівник продажів", "68000", "SALES", date(2019, 11, 11)),
)


def seed(url: str) -> None:
    engine = make_engine(url)
    init_db(engine)
    with make_session_factory(engine)() as session:
        hr = HRService(session)
        if hr.departments.count():
            return
        for code, name in DEPARTMENTS:
            hr.create_department(code, name)
        for number, name, position, salary, department, hired in EMPLOYEES:
            hr.hire(number, name, position, salary, department, hired)
    engine.dispose()
