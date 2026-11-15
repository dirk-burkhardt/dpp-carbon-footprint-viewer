"""Startet die API: ``python -m carbon_footprint_api --aasx "repo/*.aasx"``."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Optional

import uvicorn

from .cli import parse_arguments
from .main import create_app


def main(argv: Optional[Sequence[str]] = None) -> None:
    settings = parse_arguments(argv)
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        proxy_headers=settings.forwarded_allow_ips is not None,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        server_header=False,
    )


if __name__ == "__main__":
    main()
