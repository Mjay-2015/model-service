import time
import threading

from model_service.config import AdapterRuntimeSettings
from model_service.contracts import InputContract, OutputContract
from model_service.service.pipeline import run


class BoomAdapter:
    @property
    def model_version(self) -> str:
        return "boom-1"

    def predict(self, x: InputContract):
        raise RuntimeError("kaboom")


class SlowAdapter:
    def __init__(self, sleep_s: float):
        self.sleep_s = sleep_s

    @property
    def model_version(self) -> str:
        return "slow-1"

    def predict(self, x: InputContract):
        time.sleep(self.sleep_s)
        return x


class CountingAdapter:
    def __init__(self):
        self.calls = 0
        self.lock = threading.Lock()

    @property
    def model_version(self) -> str:
        return "counting-1"

    def predict(self, x: InputContract):
        with self.lock:
            self.calls += 1
        raise RuntimeError("always")


class BlockingAdapter:
    def __init__(self, sleep_s: float):
        self.sleep_s = sleep_s

    @property
    def model_version(self) -> str:
        return "blocking-1"

    def predict(self, x: InputContract):
        time.sleep(self.sleep_s)
        return OutputContract(model_version=self.model_version, output_text=x.text)


def test_pipeline_falls_back_on_error():
    x = InputContract(text="hello")
    y = run(BoomAdapter(), x, timeout_s=1.0)
    assert y.ok is False
    assert "RuntimeError" in (y.error or "")
    assert y.output_text == ""
    assert y.model_version == "boom-1"


def test_pipeline_timeout_with_retries_still_times_out():
    x = InputContract(text="hello")
    settings = AdapterRuntimeSettings(retry_attempts=3, retry_backoff_base_s=0.01, retry_jitter_s=0.0)
    y = run(SlowAdapter(sleep_s=0.2), x, timeout_s=0.05, runtime_settings=settings)
    assert y.ok is False
    assert "timeout" in (y.error or "")


def test_pipeline_retries_before_fallback():
    x = InputContract(text="hello")
    adapter = CountingAdapter()
    settings = AdapterRuntimeSettings(retry_attempts=2, retry_backoff_base_s=0.0, retry_jitter_s=0.0)
    y = run(adapter, x, timeout_s=0.05, runtime_settings=settings)
    assert y.ok is False
    assert adapter.calls == 2


def test_pipeline_respects_concurrency_limit():
    x = InputContract(text="hello")
    adapter = BlockingAdapter(sleep_s=0.2)
    settings = AdapterRuntimeSettings(max_concurrency=1)
    results: list[InputContract] = []

    def _call():
        results.append(run(adapter, x, timeout_s=1.0, runtime_settings=settings))

    start = time.perf_counter()
    t1 = threading.Thread(target=_call)
    t2 = threading.Thread(target=_call)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    elapsed = time.perf_counter() - start
    assert len(results) == 2
    assert elapsed >= 0.4  # ~0.2s per call serialized by semaphore


def test_pipeline_respects_rate_limit():
    x = InputContract(text="hello")
    adapter = BlockingAdapter(sleep_s=0.01)
    settings = AdapterRuntimeSettings(rate_limit_per_second=1.0, retry_jitter_s=0.0)
    start = time.perf_counter()
    run(adapter, x, timeout_s=1.0, runtime_settings=settings)
    run(adapter, x, timeout_s=1.0, runtime_settings=settings)
    elapsed = time.perf_counter() - start
    assert elapsed >= 1.0  # second call waits for token refill
