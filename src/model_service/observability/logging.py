from __future__ import annotations

import logging
import os


def _resolve_level() -> int:
    raw = os.getenv("MODEL_SERVICE_LOG_LEVEL", "INFO").upper()
    resolved = logging.getLevelName(raw)
    return resolved if isinstance(resolved, int) else logging.INFO


def get_logger(name: str = "model_service") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(_resolve_level())
    return logger
