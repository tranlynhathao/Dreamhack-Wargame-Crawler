"""Logging helpers."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure a single process-wide logging format."""

    logger = logging.getLogger("dreamhack_local")
    if logger.handlers:
        logger.setLevel(level.upper())
        return logger

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    return logger
