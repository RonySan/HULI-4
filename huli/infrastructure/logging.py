"""Configuração de logging estruturado da Huli."""

from __future__ import annotations

import logging
from typing import TextIO

from huli.infrastructure.config import Settings


_LOG_FORMAT = (
    "%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s"
)


def configure_logging(settings: Settings, stream: TextIO | None = None) -> logging.Logger:
    """Configura e devolve o logger raiz da aplicação Huli."""
    logger = logging.getLogger("huli")
    logger.setLevel(getattr(logging, settings.log_level))
    logger.propagate = False

    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
    return logger
