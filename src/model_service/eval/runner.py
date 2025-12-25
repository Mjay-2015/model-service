from __future__ import annotations

import json
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable
from pathlib import Path

from model_service.contracts import coerce_input
from model_service.model.base import ModelAdapter
from model_service.service.pipeline import run


@dataclass(frozen=True)
class TraceSample:
    index: int
    input: dict
    output: dict

    def as_dict(self) -> dict:
        return {"index": self.index, "input": self.input, "output": self.output}


@dataclass(frozen=True)
class StopConditions:
    success_rate_lt: float | None = None

    def __post_init__(self) -> None:
        if self.success_rate_lt is not None and not 0.0 <= self.success_rate_lt <= 1.0:
            raise ValueError("success_rate_lt must be between 0.0 and 1.0")

    def should_stop(self, ok: int, failed: int) -> tuple[bool, str | None]:
        if self.success_rate_lt is not None:
            total = ok + failed
            if total > 0 and (ok / total) < self.success_rate_lt:
                return True, f"success_rate<{self.success_rate_lt}"
        return False, None


@dataclass(frozen=True)
class EvalReport:
    total: int
    ok: int
    failed: int
    p50_ms: float
    p95_ms: float
    success_rate: float
    stopped_early: bool
    stop_reason: str | None
    traces: tuple[TraceSample, ...]
    html_summary_path: str | None = None

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "ok": self.ok,
            "failed": self.failed,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "success_rate": self.success_rate,
            "stopped_early": self.stopped_early,
            "stop_reason": self.stop_reason,
            "traces": [t.as_dict() for t in self.traces],
            "html_summary_path": self.html_summary_path,
        }


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


def _render_html_summary(report: EvalReport) -> str:
    trace_rows = "\n".join(
        f"<tr><td>{t.index}</td><td><pre>{html.escape(json.dumps(t.input, ensure_ascii=False, indent=2))}</pre></td>"
        f"<td><pre>{html.escape(json.dumps(t.output, ensure_ascii=False, indent=2))}</pre></td></tr>"
        for t in report.traces
    )
    stop_reason = report.stop_reason or "n/a"
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>model-service eval summary</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
      th {{ background-color: #f4f4f4; text-align: left; }}
      pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; }}
    </style>
  </head>
  <body>
    <h1>Evaluation summary</h1>
    <ul>
      <li>Total processed: {report.total}</li>
      <li>OK: {report.ok}</li>
      <li>Failed: {report.failed}</li>
      <li>Success rate: {report.success_rate:.2%}</li>
      <li>p50 latency (ms): {report.p50_ms:.2f}</li>
      <li>p95 latency (ms): {report.p95_ms:.2f}</li>
      <li>Stopped early: {report.stopped_early}</li>
      <li>Stop reason: {stop_reason}</li>
    </ul>
    <h2>Traces</h2>
    <table>
      <thead>
        <tr><th>#</th><th>Input</th><th>Output</th></tr>
      </thead>
      <tbody>
        {trace_rows}
      </tbody>
    </table>
  </body>
</html>
"""


def evaluate(
    model: ModelAdapter,
    dataset_path: str | Path,
    timeout_s: float,
    *,
    concurrency: int = 1,
    burst_size: int | None = None,
    stop_conditions: StopConditions | None = None,
    redactor: Callable[[dict], dict] | None = None,
    html_summary_path: str | Path | None = None,
) -> EvalReport:
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if burst_size is not None and burst_size < 1:
        raise ValueError("burst_size must be >= 1")

    rows = load_jsonl(dataset_path)
    latencies: list[float] = []
    traces: list[TraceSample] = []
    ok = 0
    failed = 0
    stop_reason: str | None = None
    burst = burst_size or concurrency

    def _execute(idx: int, row: dict) -> tuple[int, dict, dict, float, bool]:
        x = coerce_input(row)
        y = run(model, x, timeout_s=timeout_s)
        latency = float(y.latency_ms or 0.0)
        return idx, row, y.model_dump(), latency, bool(y.ok)

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for start in range(0, len(rows), burst):
            batch = rows[start : start + burst]
            future_map = {
                ex.submit(_execute, start + i, row): start + i for i, row in enumerate(batch)
            }
            for fut in as_completed(future_map):
                idx, raw_row, out, latency, ok_flag = fut.result()
                latencies.append(latency)
                if ok_flag:
                    ok += 1
                else:
                    failed += 1
                trace_input = redactor(dict(raw_row)) if redactor else raw_row
                traces.append(
                    TraceSample(
                        index=idx,
                        input=trace_input,
                        output=out,
                    )
                )
                if stop_conditions:
                    should_stop, reason = stop_conditions.should_stop(ok, failed)
                    if should_stop:
                        stop_reason = reason
                        for pending in future_map:
                            pending.cancel()
                        break
            if stop_reason:
                break

    processed = ok + failed
    success_rate = ok / processed if processed else 0.0
    traces_sorted = tuple(sorted(traces, key=lambda t: t.index))
    report = EvalReport(
        total=processed,
        ok=ok,
        failed=failed,
        p50_ms=_percentile(latencies, 50),
        p95_ms=_percentile(latencies, 95),
        success_rate=success_rate,
        stopped_early=stop_reason is not None,
        stop_reason=stop_reason,
        traces=traces_sorted,
        html_summary_path=str(html_summary_path) if html_summary_path else None,
    )

    if html_summary_path:
        Path(html_summary_path).write_text(_render_html_summary(report), encoding="utf-8")

    return report
