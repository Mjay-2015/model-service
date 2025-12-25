from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from model_service.contracts import coerce_input
from model_service.model.base import ModelAdapter
from model_service.config import AdapterRuntimeSettings
from model_service.service.pipeline import run


@dataclass(frozen=True)
class EvalReport:
    total: int
    ok: int
    failed: int
    p50_ms: float
    p95_ms: float


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(round((p / 100.0) * (len(s) - 1)))
    return float(s[idx])


def load_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    rows: list[dict] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def evaluate(
    model: ModelAdapter,
    dataset_path: str | Path,
    timeout_s: float,
    runtime_settings: AdapterRuntimeSettings | None = None,
) -> EvalReport:
    rows = load_jsonl(dataset_path)
    latencies: list[float] = []
    ok = 0
    failed = 0

    for row in rows:
        x = coerce_input(row)
        y = run(model, x, timeout_s=timeout_s, runtime_settings=runtime_settings)
        latencies.append(float(y.latency_ms or 0.0))
        if y.ok:
            ok += 1
        else:
            failed += 1

    return EvalReport(
        total=len(rows),
        ok=ok,
        failed=failed,
        p50_ms=_percentile(latencies, 50),
        p95_ms=_percentile(latencies, 95),
    )
