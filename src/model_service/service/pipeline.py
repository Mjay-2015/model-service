from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

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


def run(model: ModelAdapter, x: InputContract, timeout_s: float) -> OutputContract:
    """
    Software-first orchestration:
    - time-bounded call
    - contract-valid outputs always
    - safe fallback on failure
    """
    start = time.perf_counter()
    mv = getattr(model, "model_version", "unknown")

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(model.predict, x)
            y = fut.result(timeout=timeout_s)

        latency_ms = (time.perf_counter() - start) * 1000
        # Ensure latency included (non-invasive)
        return y.model_copy(update={"latency_ms": latency_ms})

    except FuturesTimeoutError:
        latency_ms = (time.perf_counter() - start) * 1000
        log.info("timeout: model call exceeded %.2fs", timeout_s)
        return _fallback(mv, f"timeout after {timeout_s:.2f}s", latency_ms)

    except Exception as e:  # noqa: BLE001 (intentional boundary)
        latency_ms = (time.perf_counter() - start) * 1000
        log.info("error: model call failed (%s)", type(e).__name__)
        return _fallback(mv, f"{type(e).__name__}: {e}", latency_ms)
