"""Entry point: demonstration of the streaming pipeline (variant 6)."""

import sys
from collections import Counter
from itertools import islice, pairwise
from pathlib import Path

from employee_stream.analytics import (
    calculate_statistics,
    count_by_department,
    highest_paid,
    running_payroll,
    streaming_average,
    streaming_payroll,
)
from employee_stream.batches import batched, export_batches, summarize_batch
from employee_stream.filters import find_employee
from employee_stream.generate import dataset_path, generate_file
from employee_stream.pipeline import build_pipeline
from employee_stream.readers import RecordFile
from employee_stream.transformations import short_view
from employee_stream.utils import employee_ids, flatten, take


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    path = dataset_path(size)
    if not path.exists():
        generate_file(path, size)
    print(f"Джерело: {path.as_posix()} ({size} records)")

    # 1. Власний iterator class: RecordFile можна обходити повторно
    sample = RecordFile(Path("data/sample.csv"))
    print(f"\n1. RecordFile(sample.csv): рядків {sum(1 for _ in sample)}, "
          f"повторний обхід {len(list(sample))}")

    # 2. Фільтр за відділом + lazy filter за рівнем зарплати, перші 3 (islice)
    print("\n2. Перші 3 працівники відділу «Фінанси» із зарплатою 70 000..80 000 (islice):")
    query = build_pipeline(path, department="фінанси", min_salary=70_000, max_salary=80_000)
    for line in short_view(islice(query, 3)):
        print("  ", line)

    # 3. Пошук за employee_id з early termination
    stats: Counter[str] = Counter()
    found = find_employee(build_pipeline(path, stats=stats), "E100250")
    print(f"\n3. Пошук E100250: {found.name}, {found.department}, {money(found.salary)}; "
          f"прочитано рядків: {stats['rows']} з {size}")

    # 4. Повна потокова статистика + streaming validation
    stats = Counter()
    result = calculate_statistics(build_pipeline(path, stats=stats))
    invalid = {k.split(":")[1]: v for k, v in stats.items() if k.startswith("invalid")}
    print("\n4. Статистика (один прохід, без матеріалізації):")
    print(f"   рядків {stats['rows']}, валідних {stats['valid']}, некоректних "
          f"{sum(invalid.values())}")
    print(f"   причини: {invalid}")
    print(f"   працівників за відділами: {result['departments']}")
    print(f"   фонд оплати праці: {money(result['payroll'])} грн")
    print(f"   середня зарплата: {money(result['average'])} грн")
    top = result["highest"]
    print(f"   максимальна зарплата: {top.employee_id} {top.name} ({top.department}) "
          f"{money(top.salary)}")

    # 5. Окремі потокові функції: generator expression, max, Counter
    it_salaries = (e.salary for e in build_pipeline(path, department="IT"))
    print(f"\n5. Середня зарплата в IT (streaming average): {money(streaming_average(it_salaries))}")
    print(f"   фонд оплати праці HR (streaming_payroll): "
          f"{money(streaming_payroll(build_pipeline(path, department='HR')))}")
    top_sales = highest_paid(build_pipeline(path, department="Продажі"))
    print(f"   найвища зарплата в продажах: {top_sales.name} {money(top_sales.salary)}")
    print(f"   count_by_department: {dict(count_by_department(build_pipeline(path)))}")

    # 6. Batch processing + groupby + pairwise + accumulate + batch export
    print("\n6. Batch processing (batch = 25 000), перші 3 batches:")
    payrolls = []
    for number, batch in enumerate(islice(batched(build_pipeline(path), 25_000), 3), 1):
        summary = summarize_batch(batch)
        payrolls.append(summary["payroll"])
        print(f"   #{number}: {int(summary['size'])} записів, фонд {money(summary['payroll'])}, "
              f"IT {money(summary['IT'])}, Логістика {money(summary['Логістика'])}")
    changes = [round(b - a, 2) for a, b in pairwise(payrolls)]
    print(f"   зміна фонду між batches (pairwise): {[money(c) for c in changes]}")
    cumulative = list(islice(running_payroll(build_pipeline(path)), 4))
    print(f"   накопичений фонд перших 4 працівників (accumulate): {[money(c) for c in cumulative]}")
    files = list(export_batches(build_pipeline(path, department="IT"), Path("output/batches"),
                                10_000, prefix="it"))
    print(f"   batch export IT: {len(files)} файлів, {files[0].as_posix()} ... {files[-1].name}")

    # 7. Нескінченний generator + islice, yield from
    print(f"\n7. employee_ids() + islice: {take(3, employee_ids())}")
    print(f"   flatten([1, [2, [3, [4]]], 5]): {list(flatten([1, [2, [3, [4]]], 5]))}")


if __name__ == "__main__":
    main()
