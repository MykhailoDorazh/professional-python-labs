# Employee Manager

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №1, варіант 6 — «Система обліку працівників».

## Description

Консольний застосунок для обліку працівників. Для працівника зберігаються табельний номер
(`E` + 4 цифри), ПІБ, посада, відділ і зарплата (не від'ємна).

Можливості:

- список працівників і пошук за відділом;
- середня і максимальна зарплата, фонд оплати праці (сума зарплат);
- додавання працівника, зміна зарплати й посади, переведення до іншого відділу;
- пошук за кількома критеріями (частина ПІБ, відділ, діапазон зарплати);
- сортування, статистика, підсумки за відділами;
- меню з введенням даних із клавіатури та перевіркою введення.

## Requirements

Python 3.11+

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

## Run

Демонстраційний сценарій:

```
python -m employee_manager.main
```

Меню з введенням із клавіатури:

```
employee-manager --menu
```

## Tests

```
python -m unittest discover tests -v
```

## Project structure

```
src/employee_manager/
    config.py      constants (currency, salary limits, id format)
    exceptions.py  custom exceptions
    models.py      Employee dataclass with validation
    services.py    business logic
    console.py     keyboard input and tables
    main.py        entry point: demo and menu
tests/test_services.py
```

## Author

Student: Дораж Михайло
Group: ФеП-31
