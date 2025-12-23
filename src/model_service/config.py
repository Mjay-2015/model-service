from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # Keep it intentionally small. Grow only when you must.
    default_timeout_s: float = float(os.getenv("MODEL_SERVICE_TIMEOUT_S", "2.0"))
    adapter: str = os.getenv("MODEL_SERVICE_ADAPTER", "stub")  # "stub" for now


def load_settings() -> Settings:
    return Settings()
