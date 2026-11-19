"""Entry point: demonstration of the streaming pipeline (variant 4)."""

import sys
from collections import Counter
from itertools import islice, pairwise
from pathlib import Path

from bank_stream.analytics import calculate_statistics, running_totals, streaming_average
from bank_stream.batches import batched, summarize_batch
from bank_stream.filters import find_account
from bank_stream.generate import dataset_path, generate_file
from bank_stream.pipeline import build_pipeline
from bank_stream.readers import RecordFile
from bank_stream.transformations import short_view
from bank_stream.utils import account_numbers, flatten, take


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

    # 2. Перші N рахунків за умовою (islice): клієнт 'Коваль', баланс >= 90 000
    print("\n2. Перші 3 рахунки клієнтів 'Коваль' з балансом >= 90 000 (islice):")
    for line in short_view(islice(build_pipeline(path, client="коваль", min_balance=90_000), 3)):
        print("  ", line)

    # 3. Пошук за account_number з early termination
    stats: Counter[str] = Counter()
    found = find_account(build_pipeline(path, stats=stats), "UA10000250")
    print(f"\n3. Пошук UA10000250: {found.client}, баланс {money(found.balance_after)}; "
          f"прочитано рядків: {stats['rows']} з {size}")

    # 4. Повна потокова статистика + підрахунок invalid records
    stats = Counter()
    result = calculate_statistics(build_pipeline(path, stats=stats))
    invalid = {k.split(":")[1]: v for k, v in stats.items() if k.startswith("invalid")}
    print("\n4. Статистика (один прохід, без матеріалізації):")
    print(f"   рядків {stats['rows']}, валідних {stats['valid']}, некоректних {sum(invalid.values())}")
    print(f"   причини: {invalid}")
    print(f"   операції: {result['operations']}")
    print(f"   загальна сума коштів: {money(result['total_funds'])} грн")
    print(f"   середній баланс: {money(result['average'])} грн")
    r = result["richest"]
    print(f"   найбільший баланс: {r.account_number} {r.client} {money(r.balance_after)}")

    # 5. Generator expression + streaming average
    deposits = (rec.amount for rec in build_pipeline(path) if rec.operation == "deposit")
    print(f"\n5. Середня сума поповнення (generator expression): {streaming_average(deposits):.2f}")

    # 6. Batch processing + groupby + pairwise + accumulate
    print("\n6. Batch processing (batch = 25 000), перші 3 batches:")
    batch_funds = []
    for number, batch in enumerate(islice(batched(build_pipeline(path), 25_000), 3), 1):
        summary = summarize_batch(batch)
        batch_funds.append(summary["funds"])
        print(f"   #{number}: {int(summary['size'])} записів, поповнення {money(summary['deposit'])}, "
              f"списання {money(summary['withdraw'])}, відхилено {money(summary['withdraw_rejected'])}")
    changes = [round(b - a, 2) for a, b in pairwise(batch_funds)]
    print(f"   зміна суми коштів між batches (pairwise): {[money(c) for c in changes]}")
    cumulative = list(islice(running_totals(build_pipeline(path)), 5))
    print(f"   накопичена сума перших 5 рахунків (accumulate): {[money(c) for c in cumulative]}")

    # 7. Нескінченний generator + islice, yield from
    print(f"\n7. account_numbers() + islice: {take(3, account_numbers())}")
    print(f"   flatten([1, [2, [3, [4]]], 5]): {list(flatten([1, [2, [3, [4]]], 5]))}")


if __name__ == "__main__":
    main()
