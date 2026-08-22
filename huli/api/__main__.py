"""Executa a API local da Huli."""

from __future__ import annotations

import uvicorn

from huli.api import create_app
from huli.infrastructure import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        create_app(),
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
