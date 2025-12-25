from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any


@dataclass(frozen=True)
class AdapterRuntimeSettings:
    max_concurrency: int | None = None
    rate_limit_per_second: float | None = None
    retry_attempts: int = 1
    retry_backoff_base_s: float = 0.1
    retry_jitter_s: float = 0.05


def _parse_adapter_settings(raw: dict[str, Any]) -> AdapterRuntimeSettings:
    def _int_or_none(val: Any) -> int | None:
        if val is None:
            return None
        try:
            parsed = int(val)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _float_or_none(val: Any) -> float | None:
        if val is None:
            return None
        try:
            parsed = float(val)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    retry_attempts = _int_or_none(raw.get("retry_attempts")) or 1
    return AdapterRuntimeSettings(
        max_concurrency=_int_or_none(raw.get("max_concurrency")),
        rate_limit_per_second=_float_or_none(raw.get("rate_limit_per_second")),
        retry_attempts=retry_attempts,
        retry_backoff_base_s=_float_or_none(raw.get("retry_backoff_base_s")) or 0.1,
        retry_jitter_s=_float_or_none(raw.get("retry_jitter_s")) or 0.05,
    )


def _load_adapter_overrides() -> dict[str, AdapterRuntimeSettings]:
    raw = os.getenv("MODEL_SERVICE_ADAPTER_SETTINGS")
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    overrides: dict[str, AdapterRuntimeSettings] = {}
    if not isinstance(payload, dict):
        return overrides

    for name, cfg in payload.items():
        if not isinstance(cfg, dict):
            continue
        overrides[str(name)] = _parse_adapter_settings(cfg)
    return overrides


@dataclass(frozen=True)
class Settings:
    # Keep it intentionally small. Grow only when you must.
    default_timeout_s: float
    adapter: str
    adapter_overrides: dict[str, AdapterRuntimeSettings]


def _float_env(key: str, default: float, min_value: float | None = None) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if min_value is not None and value <= min_value:
        return default
    return value


def load_settings() -> Settings:
    return Settings(
        default_timeout_s=_float_env("MODEL_SERVICE_TIMEOUT_S", 2.0, min_value=0.0),
        adapter=os.getenv("MODEL_SERVICE_ADAPTER", "stub"),
        adapter_overrides=_load_adapter_overrides(),
    )
