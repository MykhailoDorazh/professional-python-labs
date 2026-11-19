# Професійний Python — лабораторні роботи

Студент: Дораж Михайло, група ФеП-31
Викладач: Куньо Іван Михайлович
Варіант 4 — система банківських рахунків (один проєкт розвивається від ЛР №1 до ЛР №10).

| ЛР | Тема | Каталог | Звіт |
|---|---|---|---|
| 1 | Структура Python-проєкту, меню, валідація | [Lab1](Lab1) | [PDF](reports/Lab1_Дораж_ФеП-31.pdf) |
| 2 | Колекції, функції, декоратори | [Lab2](Lab2) | [PDF](reports/Lab2_Дораж_ФеП-31.pdf) |
| 3 | Ітератори, генератори, itertools | [Lab3](Lab3) | [PDF](reports/Lab3_Дораж_ФеП-31.pdf) |
| 4 | ООП, типізація, mypy | [Lab4](Lab4) | [PDF](reports/Lab4_Дораж_ФеП-31.pdf) |
| 5 | Обробка помилок, файли, YAML, логування | [Lab5](Lab5) | [PDF](reports/Lab5_Дораж_ФеП-31.pdf) |
| 6 | Автоматизоване тестування (pytest, coverage) | [Lab6](Lab6) | [PDF](reports/Lab6_Дораж_ФеП-31.pdf) |
| 7 | Бази даних: SQLite, SQLAlchemy, Alembic | [Lab7](Lab7) | [PDF](reports/Lab7_Дораж_ФеП-31.pdf) |
| 8 | REST API, асинхронне програмування | [Lab8](Lab8) | [PDF](reports/Lab8_Дораж_ФеП-31.pdf) |
| 9 | Паралельність, профілювання, оптимізація | [Lab9](Lab9) | [PDF](reports/Lab9_Дораж_ФеП-31.pdf) |
| 10 | Production Python: Docker, CI/CD, packaging | [Lab10](Lab10) | [PDF](reports/Lab10_Дораж_ФеП-31.pdf) |

Кожна лабораторна — окремий Python-проєкт (src-layout, `pyproject.toml`, tests) зі своїм README.
Історію комітів кожної роботи збережено (`git log -- LabN`).

## Запуск будь-якої лабораторної

```
cd LabN
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Далі — команди з README відповідної лабораторної (`pytest`, `python -m ...`).

## CI

`.github/workflows/lab10-ci.yml` — pipeline фінального проєкту (ЛР №10): ruff, mypy, pytest +
coverage, wheel/sdist, Docker build і перевірка `/health`.
