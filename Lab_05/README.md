# Bank IO

Навчальний проєкт з дисципліни «Професійний Python».
Лабораторна робота №5, варіант 4 — «Імпорт та експорт системи банківських рахунків».

## Input schema

CSV `account_number,client,balance,operation,amount`:

- `account_number` — `UA` + 8 цифр;
- `client` — непорожнє ім'я;
- `balance` — число >= 0;
- `operation` — одна з `allowed_operations` (`deposit`, `withdraw`);
- `amount` — число в межах (0, `max_amount`];
- після `withdraw` баланс не може стати від'ємним.

## Pipeline

```
config.yaml -> load_config() -> validate_config()
data/operations.csv -> CsvImporter.read() -> parse_operation()
    valid   -> Operation -> export_json() -> AtomicWriter (.tmp -> replace)
    invalid -> warning log (маскований номер) -> skip (tolerant) / abort (strict)
-> errors.csv, summary.json, logs/application.log
```

## Run

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
python -m bank_io.main                 # tolerant mode (skip_invalid: true)
python -m bank_io.main --strict        # strict mode
python -m bank_io.experiments          # 5 experiments
python -m unittest discover tests
```

Змінні середовища `BANK_IO_INPUT` і `BANK_IO_SKIP_INVALID` перекривають значення з `config.yaml`.

## Author

Student: Дораж Михайло
Group: ФеП-31
