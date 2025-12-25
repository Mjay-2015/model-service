from pathlib import Path

from model_service.contracts import OutputContract
from model_service.model.stub import StubAdapter
from model_service.eval.runner import StopConditions, evaluate


def test_evaluate_counts_rows(tmp_path: Path):
    ds = tmp_path / "d.jsonl"
    ds.write_text('{"text":"a"}\n{"text":"bb"}\n', encoding="utf-8")
    r = evaluate(StubAdapter(), ds, timeout_s=1.0)
    assert r.total == 2
    assert r.ok == 2
    assert r.failed == 0
    assert r.success_rate == 1.0
    assert len(r.traces) == 2
    assert r.traces[0].index == 0
    assert r.traces[1].index == 1
    assert r.stopped_early is False


def test_evaluate_stops_on_success_rate(tmp_path: Path):
    class FailFastAdapter:
        @property
        def model_version(self) -> str:
            return "fail-1"

        def predict(self, x):
            return OutputContract(
                ok=False,
                model_version=self.model_version,
                output_text="",
                error="nope",
            )

    ds = tmp_path / "f.jsonl"
    ds.write_text('{"text":"bad"}\n{"text":"still bad"}\n', encoding="utf-8")
    r = evaluate(
        FailFastAdapter(),
        ds,
        timeout_s=1.0,
        stop_conditions=StopConditions(success_rate_lt=0.5),
    )
    assert r.stopped_early is True
    assert r.stop_reason == "success_rate<0.5"
    assert r.total == 1
    assert r.ok == 0
    assert r.failed == 1


def test_trace_redaction_and_html(tmp_path: Path):
    ds = tmp_path / "t.jsonl"
    ds.write_text('{"text":"secret"}\n', encoding="utf-8")
    html_path = tmp_path / "report.html"
    r = evaluate(
        StubAdapter(),
        ds,
        timeout_s=1.0,
        redactor=lambda row: {"text": "[redacted]"},
        html_summary_path=html_path,
    )
    assert r.traces[0].input["text"] == "[redacted]"
    assert r.html_summary_path == str(html_path)
    html_body = html_path.read_text(encoding="utf-8")
    assert "[redacted]" in html_body
    assert "secret" not in html_body
