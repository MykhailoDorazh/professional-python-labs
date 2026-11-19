# Bank Accounts

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №1, варіант 4 — «Система банківських рахунків».

## Description

Консольний застосунок для роботи з банківськими рахунками. Для рахунку
зберігаються ім'я клієнта, номер рахунку (`UA` + 6 цифр) і баланс.

Можливості:

- поповнення та списання коштів (від'ємний баланс заборонено);
- перевірка балансу;
- пошук рахунку за номером, пошук за клієнтом і діапазоном балансу;
- обчислення загальної суми коштів і статистики (середній, min, max);
- сортування рахунків;
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
python -m bank_accounts.main
```

Меню з введенням із клавіатури:

```
python -m bank_accounts.main --menu
```

або через console command:

```
bank-accounts --menu
```

Приклад запуску:

```
Пошук UA100003: Андрій Мельник, баланс 2 150.75 грн
Поповнення на 850.25: новий баланс 3001.00 грн
Списання 1 000.00: новий баланс 2001.00 грн
Списання 100.00 відхилено: Недостатньо коштів на UA100005: баланс 0.00, запит 100.00
```

## Tests

```
python -m unittest discover tests -v
```

## Project structure

- `src/bank_accounts/config.py` — configuration constants.
- `src/bank_accounts/exceptions.py` — custom exceptions.
- `src/bank_accounts/models.py` — data model `Account` (dataclass).
- `src/bank_accounts/services.py` — business logic.
- `src/bank_accounts/console.py` — console input/output.
- `src/bank_accounts/main.py` — application entry point.
- `tests/test_services.py` — tests of the business logic.

## Author

Student: Дораж Михайло
Group: ФеП-31
