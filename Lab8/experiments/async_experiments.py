"""Async experiments with a simulated slow bank API (100 ms per request).

1) sequential awaits vs asyncio.gather vs gather + Semaphore;
2) retry with exponential backoff on a flaky server;
3) timeout of a request that hangs.
"""

import asyncio
import logging
import sys
import time

import httpx

from bank_api.external_api import BankApiClient

LATENCY = 0.1
N = 20


async def slow_api(request: httpx.Request) -> httpx.Response:
    await asyncio.sleep(LATENCY)  # network + server time
    account_id = int(request.url.path.split("/")[2])
    if request.url.path.endswith("/transactions"):
        return httpx.Response(200, json=[])
    return httpx.Response(200, json={"id": account_id, "balance": "100.00"})


async def experiment_concurrency() -> None:
    print(f"1) {N} рахунків x 2 запити (баланс + історія), затримка {LATENCY * 1000:.0f} мс")
    ids = list(range(1, N + 1))

    async with BankApiClient("http://bank", transport=httpx.MockTransport(slow_api),
                             concurrency=1000) as client:
        t = time.perf_counter()
        for i in ids:  # one request after another
            await client.get_account(i)
            await client.get_history(i)
        print(f"   послідовно (await у циклі)  : {time.perf_counter() - t:6.2f} s")

    for limit in (1000, 10, 5, 2):
        async with BankApiClient("http://bank", transport=httpx.MockTransport(slow_api),
                                 concurrency=limit) as client:
            t = time.perf_counter()
            await client.snapshots(ids)
            name = "gather без обмеження" if limit == 1000 else f"gather + Semaphore({limit})"
            print(f"   {name:<28}: {time.perf_counter() - t:6.2f} s, "
                  f"max in flight = {client.max_in_flight}")


async def experiment_retry() -> None:
    print("2) retry: сервер двічі відповідає 503, потім 200")
    state = {"n": 0}

    async def flaky(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        return httpx.Response(503) if state["n"] <= 2 else httpx.Response(200, json={"id": 1})

    async with BankApiClient("http://bank", transport=httpx.MockTransport(flaky),
                             retries=3, backoff=0.2) as client:
        t = time.perf_counter()
        print(f"   результат: {await client.get_account(1)}, спроб: {client.attempts}, "
              f"час: {time.perf_counter() - t:.2f} s (backoff 0.2 + 0.4)")


async def experiment_timeout() -> None:
    print("3) timeout: справжній TCP-сервер приймає з'єднання і не відповідає")

    async def hang(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await asyncio.sleep(5)
        writer.close()

    server = await asyncio.start_server(hang, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with BankApiClient(f"http://127.0.0.1:{port}", timeout=0.3, retries=2,
                             backoff=0.1) as client:
        t = time.perf_counter()
        try:
            await client.get_account(1)
        except httpx.TimeoutException as error:
            print(f"   {type(error).__name__} через {time.perf_counter() - t:.2f} s "
                  f"(2 спроби x 0.3 s + backoff 0.1 s), спроб: {client.attempts}")
    server.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="   %(levelname)s %(message)s",
                        stream=sys.stdout)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    await experiment_concurrency()
    await experiment_retry()
    await experiment_timeout()


if __name__ == "__main__":
    asyncio.run(main())
