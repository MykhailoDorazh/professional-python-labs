"""Input data set: bank accounts as a list of dicts."""

# tuple: фіксований, незмінний перелік допустимих типів рахунку.
ACCOUNT_TYPES: tuple[str, ...] = (
    "поточний",
    "депозитний",
    "зарплатний",
    "кредитний",
)

# list[dict]: упорядкований змінюваний набір записів (JSON-like data).
accounts: list[dict] = [
    {"number": "UA100001", "client": "Іван Петренко", "balance": 12_500.00, "type": "поточний"},
    {"number": "UA100002", "client": "Олена Коваль", "balance": 48_300.50, "type": "депозитний"},
    {"number": "UA100003", "client": "Андрій Мельник", "balance": 2_150.75, "type": "зарплатний"},
    {"number": "UA100004", "client": "Марія Бондар", "balance": 91_000.00, "type": "депозитний"},
    {"number": "UA100005", "client": "Олег Шевченко", "balance": 0.00, "type": "кредитний"},
    {"number": "UA100006", "client": "Іван Петренко", "balance": 150_000.00, "type": "депозитний"},
    {"number": "UA100007", "client": "Наталія Гнатюк", "balance": 7_820.40, "type": "поточний"},
    {"number": "UA100008", "client": "Андрій Мельник", "balance": 15_640.00, "type": "поточний"},
    {"number": "UA100009", "client": "Тарас Новак", "balance": 950.00, "type": "кредитний"},
    {"number": "UA100010", "client": "Олена Коваль", "balance": 23_400.00, "type": "зарплатний"},
]
