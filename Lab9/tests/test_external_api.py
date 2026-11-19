"""BankApiClient: retry, backoff, timeout, Semaphore — external HTTP service is mocked."""

import asyncio
import time
from collections.abc import Callable

import httpx
import pytest

from bank_perf.external_api import BankApiClient, RetryableStatusError

pytestmark = pytest.mark.asyncio

Handler = Callable[[httpx.Request], httpx.Response]


def account_json(request: httpx.Request) -> httpx.Response:
    account_id = int(request.url.path.split("/")[2])
    if request.url.path.endswith("/transactions"):
        return httpx.Response(200, json=[{"kind": "deposit"}])
    return httpx.Response(200, json={"id": account_id, "number": f"UA{account_id:08d}",
                                     "balance": "10.00"})


def make_client(handler: Handler, **kwargs: object) -> BankApiClient:
    return BankApiClient("http://bank.test", transport=httpx.MockTransport(handler),
                         backoff=0.01, **kwargs)  # type: ignore[arg-type]


async def test_snapshot_uses_two_concurrent_requests() -> None:
    async with make_client(account_json) as client:
        snapshot = await client.account_snapshot(7)
    assert snapshot["account"]["number"] == "UA00000007"
    assert snapshot["history"] == [{"kind": "deposit"}]
    assert client.attempts == 2


async def test_retry_after_temporary_errors() -> None:
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx.Response(503)
        return account_json(request)

    async with make_client(flaky, retries=3) as client:
        account = await client.get_account(1)
    assert account["id"] == 1
    assert calls["n"] == 3  # 503, 503, 200


async def test_retry_on_network_error_then_give_up() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with make_client(broken, retries=3) as client:
        with pytest.raises(httpx.ConnectError):
            await client.get_account(1)
    assert client.attempts == 3


async def test_client_errors_are_not_retried() -> None:
    async with make_client(lambda r: httpx.Response(404, json={"detail": "x"})) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_account(1)
    assert client.attempts == 1


async def test_exponential_backoff_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr("bank_perf.external_api.asyncio.sleep", fake_sleep)
    client = BankApiClient("http://bank.test", retries=4, backoff=0.5,
                           transport=httpx.MockTransport(lambda r: httpx.Response(502)))
    with pytest.raises(RetryableStatusError):
        await client.get_account(1)
    await client.__aexit__(None, None, None)
    assert delays == [0.5, 1.0, 2.0]


async def test_request_timeout_is_retried_then_raised() -> None:
    """A real local TCP server that never answers: httpx read timeout + retry."""
    async def hang(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await asyncio.sleep(2)
        writer.close()

    server = await asyncio.start_server(hang, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    started = time.perf_counter()
    async with BankApiClient(f"http://127.0.0.1:{port}", timeout=0.1, retries=2,
                             backoff=0.01) as client:
        with pytest.raises(httpx.ReadTimeout):
            await client.get_account(1)
    server.close()
    assert client.attempts == 2
    assert time.perf_counter() - started < 1.5


async def test_semaphore_limits_concurrency_and_gather_is_faster() -> None:
    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.05)
        return account_json(request)

    async with make_client(slow, concurrency=4) as client:  # type: ignore[arg-type]
        started = time.perf_counter()
        results = await client.snapshots(list(range(1, 11)))
        elapsed = time.perf_counter() - started
    assert len(results) == 10 and not any(isinstance(r, BaseException) for r in results)
    assert client.max_in_flight == 4           # never more than the Semaphore allows
    assert elapsed < 20 * 0.05                 # 20 requests faster than sequential 1.0 s


async def test_one_failure_does_not_cancel_other_tasks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/accounts/3"):
            return httpx.Response(404)
        return account_json(request)

    async with make_client(handler) as client:
        results = await client.snapshots([1, 2, 3, 4])
    assert [isinstance(r, BaseException) for r in results] == [False, False, True, False]


async def test_total_timeout_cancels_batch() -> None:
    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(2)
        return account_json(request)

    async with make_client(slow) as client:  # type: ignore[arg-type]
        with pytest.raises(TimeoutError):
            await client.snapshots([1, 2], total_timeout=0.1)
