# Професійний Python — лабораторні роботи

Студент: Дораж Михайло, група ФеП-31
Викладач: Куньо Іван Михайлович
Варіант 4 — система банківських рахунків (один проєкт розвивається від ЛР №1 до ЛР №10).

| ЛР | Тема | Каталог | Звіт |
|---|---|---|---|
| 1 | Структура Python-проєкту, меню, валідація | [Lab_01](Lab_01) | [PDF](Lab_01/Lab1_Дораж_ФеП-31.pdf) |
| 2 | Колекції, функції, декоратори | [Lab_02](Lab_02) | [PDF](Lab_02/Lab2_Дораж_ФеП-31.pdf) |
| 3 | Ітератори, генератори, itertools | [Lab_03](Lab_03) | [PDF](Lab_03/Lab3_Дораж_ФеП-31.pdf) |
| 4 | ООП, типізація, mypy | [Lab_04](Lab_04) | [PDF](Lab_04/Lab4_Дораж_ФеП-31.pdf) |
| 5 | Обробка помилок, файли, YAML, логування | [Lab_05](Lab_05) | [PDF](Lab_05/Lab5_Дораж_ФеП-31.pdf) |
| 6 | Автоматизоване тестування (pytest, coverage) | [Lab_06](Lab_06) | [PDF](Lab_06/Lab6_Дораж_ФеП-31.pdf) |
| 7 | Бази даних: SQLite, SQLAlchemy, Alembic | [Lab_07](Lab_07) | [PDF](Lab_07/Lab7_Дораж_ФеП-31.pdf) |
| 8 | REST API, асинхронне програмування | [Lab_08](Lab_08) | [PDF](Lab_08/Lab8_Дораж_ФеП-31.pdf) |
| 9 | Паралельність, профілювання, оптимізація | [Lab_09](Lab_09) | [PDF](Lab_09/Lab9_Дораж_ФеП-31.pdf) |
| 10 | Production Python: Docker, CI/CD, packaging | [Lab_10](Lab_10) | [PDF](Lab_10/Lab10_Дораж_ФеП-31.pdf) |

Кожна лабораторна (`Lab_01` … `Lab_10`) — окремий Python-проєкт (src-layout, `pyproject.toml`, tests) зі своїм README; PDF-звіт лежить у каталозі відповідної роботи.
Історію комітів кожної роботи збережено (`git log -- Lab_NN`).

## Запуск будь-якої лабораторної

```
cd Lab_NN
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Далі — команди з README відповідної лабораторної (`pytest`, `python -m ...`).

## CI

`.github/workflows/lab10-ci.yml` — pipeline фінального проєкту (ЛР №10): ruff, mypy, pytest +
coverage, wheel/sdist, Docker build і перевірка `/health`.
