"""Asynchronous HTTP client of the Employee API (httpx.AsyncClient).

Fetches statistics of several departments in parallel: asyncio.Task + gather,
a Semaphore that limits requests in flight, timeouts and retry with
exponential backoff.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from types import TracebackType
from typing import Any

import httpx

log = logging.getLogger("employee_api.client")

RETRY_STATUSES = {429, 502, 503, 504}


class RetryableStatusError(Exception):
    """Server answered with a temporary error status (5xx/429)."""


class EmployeeApiClient:
    """Reusable client: one connection pool for the whole lifetime (async with)."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        retries: int = 3,
        backoff: float = 0.2,
        concurrency: int = 5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.retries = retries
        self.backoff = backoff
        self.semaphore = asyncio.Semaphore(concurrency)
        self.in_flight = 0
        self.max_in_flight = 0
        self.attempts = 0
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=httpx.Timeout(timeout), transport=transport
        )

    async def __aenter__(self) -> EmployeeApiClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def request_json(self, method: str, url: str, **kwargs: Any) -> Any:
        """One HTTP request with retry and exponential backoff.

        Network errors, timeouts and 429/5xx are retried; 4xx are not
        (repeating a wrong request gives the same answer).
        """
        for attempt in range(1, self.retries + 1):
            try:
                async with self.semaphore:
                    self.attempts += 1
                    self.in_flight += 1
                    self.max_in_flight = max(self.max_in_flight, self.in_flight)
                    try:
                        response = await self._client.request(method, url, **kwargs)
                    finally:
                        self.in_flight -= 1
                if response.status_code in RETRY_STATUSES:
                    raise RetryableStatusError(f"{response.status_code} for {url}")
                response.raise_for_status()
                return response.json()
            except (httpx.TransportError, RetryableStatusError) as error:
                if attempt == self.retries:
                    log.warning("give up %s %s after %d attempts: %r", method, url, attempt, error)
                    raise
                delay = self.backoff * 2 ** (attempt - 1)
                log.info("attempt %d for %s failed (%r), retry in %.2fs", attempt, url, error, delay)
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable")  # pragma: no cover

    # ---------- API methods ----------
    async def get_statistics(self, department_id: int) -> dict[str, Any]:
        result: dict[str, Any] = await self.request_json(
            "GET", f"/departments/{department_id}/statistics")
        return result

    async def get_employees(self, department_id: int) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = await self.request_json(
            "GET", f"/departments/{department_id}/employees")
        return result

    async def department_report(self, department_id: int) -> dict[str, Any]:
        """Statistics and staff of one department: two requests at the same time."""
        statistics, employees = await asyncio.gather(
            self.get_statistics(department_id), self.get_employees(department_id)
        )
        return {"statistics": statistics, "employees": employees}

    async def statistics_of(
        self, department_ids: list[int], total_timeout: float = 10.0
    ) -> list[dict[str, Any] | BaseException]:
        """Reports of many departments concurrently; one failure does not cancel others."""
        tasks = [asyncio.create_task(self.department_report(i)) for i in department_ids]
        try:
            return await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=total_timeout
            )
        except TimeoutError:
            for task in tasks:
                task.cancel()
            raise


async def run(base_url: str, ids: list[int], concurrency: int) -> None:
    async with EmployeeApiClient(base_url, concurrency=concurrency) as client:
        health = await client.request_json("GET", "/health")
        print(f"GET /health -> {health}")
        started = time.perf_counter()
        results = await client.statistics_of(ids)
        elapsed = time.perf_counter() - started
        print(f"  {'id':<4}{'код':<7}{'осіб':>5}{'фонд':>12}{'середня':>11}{'max':>11}  top")
        for department_id, result in zip(ids, results, strict=True):
            if isinstance(result, BaseException):
                status = getattr(getattr(result, "response", None), "status_code", "?")
                print(f"  {department_id:<4}ERROR {type(result).__name__} (HTTP {status})")
                continue
            s = result["statistics"]
            print(f"  {department_id:<4}{s['code']:<7}{s['employees']:>5}{s['payroll']:>12}"
                  f"{s['average_salary']:>11}{s['max_salary']:>11}  {s['highest_paid'] or '-'}")
        print(f"{len(ids)} departments, {client.attempts} HTTP requests, "
              f"max in flight = {client.max_in_flight} (Semaphore {concurrency}), "
              f"{elapsed * 1000:.0f} ms")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Concurrent Employee API client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("ids", nargs="*", type=int, default=[1, 2, 3, 4, 5])
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(run(args.base_url, args.ids, args.concurrency))


if __name__ == "__main__":
    main()
