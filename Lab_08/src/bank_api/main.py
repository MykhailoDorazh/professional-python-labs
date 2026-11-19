"""Run the API server: ``python -m bank_api.main [--seed] [--port 8000]``."""

from __future__ import annotations

import argparse
import os

import uvicorn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Bank Accounts API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=None, help="SQLite file (BANK_DATABASE_URL by default)")
    parser.add_argument("--seed", action="store_true", help="fill an empty DB with demo data")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)
    if args.db:
        os.environ["BANK_DATABASE_URL"] = f"sqlite:///{args.db}"
    if args.seed:
        from bank_api.seed import seed

        seed(os.environ.get("BANK_DATABASE_URL", "sqlite:///bank.db"))
    uvicorn.run(
        "bank_api.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        use_colors=False if os.getenv("NO_COLOR") else None,  # https://no-color.org
    )


if __name__ == "__main__":
    main()
