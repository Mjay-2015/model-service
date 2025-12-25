from __future__ import annotations

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from contextlib import contextmanager

from model_service.config import AdapterRuntimeSettings

from model_service.contracts import InputContract, OutputContract
from model_service.model.base import ModelAdapter
from model_service.observability.logging import get_logger

log = get_logger()


def _fallback(model_version: str, err: str, latency_ms: float) -> OutputContract:
    # predictable, contract-valid output
    return OutputContract(
        ok=False,
        model_version=model_version,
        output_text="",
        error=err,
        latency_ms=latency_ms,
    )


_controls_lock = threading.Lock()
_controls: dict[int, "_AdapterControl"] = {}


class _AdapterControl:
    def __init__(self, settings: AdapterRuntimeSettings):
        self.settings = settings
        self._sem = (
            threading.BoundedSemaphore(settings.max_concurrency)
            if settings.max_concurrency
            else None
        )
        self._rate_limit = settings.rate_limit_per_second
        self._tokens = float(settings.rate_limit_per_second or 0.0)
        self._last_refill = time.perf_counter()
        self._lock = threading.Lock()

    @contextmanager
    def concurrent_slot(self):
        if self._sem is None:
            yield
            return
        self._sem.acquire()
        try:
            yield
        finally:
            self._sem.release()

    def wait_rate_limit(self):
        if not self._rate_limit:
            return
        while True:
            with self._lock:
                now = time.perf_counter()
                elapsed = now - self._last_refill
                self._last_refill = now
                self._tokens = min(
                    self._rate_limit, self._tokens + elapsed * self._rate_limit
                )
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                deficit = 1.0 - self._tokens
                wait = deficit / self._rate_limit
            time.sleep(wait)


def _get_controls(settings: AdapterRuntimeSettings, model: ModelAdapter) -> _AdapterControl:
    key = id(model)
    with _controls_lock:
        ctl = _controls.get(key)
        if ctl and ctl.settings == settings:
            return ctl
        ctl = _AdapterControl(settings)
        _controls[key] = ctl
        return ctl


def run(
    model: ModelAdapter,
    x: InputContract,
    timeout_s: float,
    runtime_settings: AdapterRuntimeSettings | None = None,
) -> OutputContract:
    """
    Software-first orchestration:
    - time-bounded call
    - contract-valid outputs always
    - safe fallback on failure
    """
    start = time.perf_counter()
    runtime = runtime_settings or AdapterRuntimeSettings()
    controls = _get_controls(runtime, model)
    mv = getattr(model, "model_version", "unknown")

    attempt = 0
    while attempt < max(1, runtime.retry_attempts):
        attempt += 1
        err: str | None = None
        controls.wait_rate_limit()
        try:
            with controls.concurrent_slot():
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(model.predict, x)
                    y = fut.result(timeout=timeout_s)

            latency_ms = (time.perf_counter() - start) * 1000
            return y.model_copy(update={"latency_ms": latency_ms})

        except FuturesTimeoutError:
            err = f"timeout after {timeout_s:.2f}s"
            log.info("timeout: model call exceeded %.2fs", timeout_s)
        except Exception as e:  # noqa: BLE001 (intentional boundary)
            err = f"{type(e).__name__}: {e}"
            log.info("error: model call failed (%s)", type(e).__name__)

        if attempt >= runtime.retry_attempts:
            latency_ms = (time.perf_counter() - start) * 1000
            return _fallback(mv, err or "unknown error", latency_ms)

        backoff = max(0.0, runtime.retry_backoff_base_s) * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, max(0.0, runtime.retry_jitter_s))
        time.sleep(backoff + jitter)
