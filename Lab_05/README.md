# Employee IO

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №5, варіант 6 — «Імпорт та експорт даних працівників».

## Input schema

CSV `employee_id,name,position,department,salary`:

- `employee_id` — `E` + 6 цифр;
- `name` (ПІБ), `position` — непорожні рядки;
- `department` — один з `allowed_departments` у `config.yaml`;
- `salary` — число в межах [0, `max_salary`].

Валідні записи із зарплатою менше `min_salary` не є помилкою — вони
відфільтровуються і не потрапляють в експорт.

## Pipeline

```
config.yaml -> load_config() -> validate_config()
data/employees.csv -> CsvImporter.read() -> parse_employee()
    valid   -> salary >= min_salary -> export_json() -> AtomicWriter (.tmp -> replace)
    invalid -> warning log (маскований номер) -> skip (tolerant) / abort (strict)
-> errors.csv, summary.json, logs/application.log
```

Логи не містять зарплат і повних ПІБ: табельний номер маскується (`E1****3`),
ПІБ — `І*** П***`, у DEBUG-лог пишеться лише діапазон зарплати.

## Run

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
python -m employee_io.main                     # tolerant mode (skip_invalid: true)
python -m employee_io.main --strict            # strict mode
python -m employee_io.main --min-salary 50000  # інший поріг фільтра
python -m employee_io.experiments              # 6 experiments
python -m unittest discover tests
```

Змінні середовища `EMPLOYEE_IO_INPUT`, `EMPLOYEE_IO_SKIP_INVALID` і
`EMPLOYEE_IO_MIN_SALARY` перекривають значення з `config.yaml`.

## Author

Student: Дораж Михайло
Group: ФеП-31
