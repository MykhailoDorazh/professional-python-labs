"""Command line entry point: ``bank-account-service [serve|migrate|version]``."""

from __future__ import annotations

import argparse
import logging

import uvicorn

from bank_account_service import __version__
from bank_account_service.config import get_settings
from bank_account_service.logging_config import configure_logging

log = logging.getLogger("bank_account_service")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bank-account-service", description="Bank accounts REST API"
    )
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="run the API server (default)")
    serve.add_argument("--migrate", action="store_true", help="apply migrations first")
    sub.add_parser("migrate", help="apply database migrations (alembic upgrade head)")
    sub.add_parser("version", help="print version")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level)
    if args.command == "version":
        print(f"bank-account-service {__version__}")
        return
    if args.command == "migrate" or getattr(args, "migrate", False):
        from bank_account_service.migrate import upgrade

        log.info("Applying migrations to %s", settings.database_url.split("://")[0])
        upgrade(settings.database_url)
        if args.command == "migrate":
            return
    log.info("Starting %s %s (env=%s)", settings.app_name, __version__, settings.app_env)
    uvicorn.run(
        "bank_account_service.api:app",
        host=settings.host,
        port=settings.port,
        log_config=None,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
