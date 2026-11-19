"""Input data set: employees as a list of dicts."""

# tuple: фіксований, незмінний перелік відділів компанії.
DEPARTMENTS: tuple[str, ...] = (
    "IT",
    "Фінанси",
    "HR",
    "Продажі",
    "Логістика",
)

# list[dict]: упорядкований змінюваний набір записів (JSON-like data).
employees: list[dict] = [
    {"id": "E1001", "name": "Іван Петренко", "position": "Розробник", "department": "IT", "salary": 52_000.00},
    {"id": "E1002", "name": "Олена Коваль", "position": "Тімлід", "department": "IT", "salary": 78_500.00},
    {"id": "E1003", "name": "Андрій Мельник", "position": "Бухгалтер", "department": "Фінанси", "salary": 31_200.00},
    {"id": "E1004", "name": "Марія Бондар", "position": "HR-менеджер", "department": "HR", "salary": 29_800.00},
    {"id": "E1005", "name": "Олег Шевченко", "position": "Аналітик", "department": "Фінанси", "salary": 41_750.50},
    {"id": "E1006", "name": "Наталія Гнатюк", "position": "Розробник", "department": "IT", "salary": 55_300.00},
    {"id": "E1007", "name": "Тарас Новак", "position": "Менеджер", "department": "Продажі", "salary": 36_400.00},
    {"id": "E1008", "name": "Софія Лисенко", "position": "Менеджер", "department": "Продажі", "salary": 38_900.00},
    {"id": "E1009", "name": "Петро Іваненко", "position": "Рекрутер", "department": "HR", "salary": 27_500.00},
    {"id": "E1010", "name": "Ірина Ткачук", "position": "Головний бухгалтер", "department": "Фінанси", "salary": 64_000.00},
]
