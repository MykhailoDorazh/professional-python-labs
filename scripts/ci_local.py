"""Run the same checks as .github/workflows/ci.yml locally and print a summary.

python scripts/ci_local.py            # lint, format, types, tests, build
python scripts/ci_local.py --docker   # + docker build and /health smoke test (WSL docker)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS: list[tuple[str, list[str]]] = [
    ("Ruff lint", ["ruff", "check", "."]),
    ("Ruff format check", ["ruff", "format", "--check", "."]),
    ("Type check (mypy)", ["mypy", "src"]),
    (
        "Tests + coverage",
        ["pytest", "-q", "--cov", "--cov-fail-under=85", "-p", "no:cacheprovider"],
    ),
    ("Build package", [sys.executable, "-m", "build"]),
]


def docker_steps(docker: list[str]) -> list[tuple[str, list[str]]]:
    script = (
        "set -e; docker rm -f api-ci >/dev/null 2>&1 || true; "
        "docker run -d --name api-ci -p 8001:8000 bank-account-service:ci >/dev/null; "
        "for i in $(seq 1 30); do curl -fsS localhost:8001/health && break; sleep 1; done; "
        "echo; docker rm -f api-ci >/dev/null"
    )
    return [
        ("Docker build", [*docker, "build", "-q", "-t", "bank-account-service:ci", "."]),
        ("Docker smoke test /health", [*docker[:-1], "bash", "-c", script]),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", action="store_true")
    args = parser.parse_args()
    steps = list(STEPS)
    if args.docker:
        wsl = ["wsl", "-d", "Ubuntu", "-u", "root", "--cd", wsl_path(ROOT), "--", "docker"]
        steps += docker_steps(wsl if shutil.which("docker") is None else ["docker"])
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    results = []
    for name, command in steps:
        print(f"\n=== {name}: {' '.join(command[-6:])}", flush=True)
        started = time.perf_counter()
        code = subprocess.run(command, cwd=ROOT).returncode
        results.append((name, code, time.perf_counter() - started))
        if code:
            break
    print("\n=== CI summary")
    for name, code, elapsed in results:
        print(f"  {'OK  ' if code == 0 else 'FAIL'}  {name:<28} {elapsed:6.1f} s")
    ok = all(code == 0 for _, code, _ in results) and len(results) == len(steps)
    print("  pipeline:", "GREEN" if ok else "RED")
    return 0 if ok else 1


def wsl_path(path: Path) -> str:
    drive, rest = path.drive, path.as_posix()[len(path.drive) :]
    return f"/mnt/{drive[0].lower()}{rest}"


if __name__ == "__main__":
    raise SystemExit(main())
