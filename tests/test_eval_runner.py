from pathlib import Path
from model_service.model.stub import StubAdapter
from model_service.eval.runner import evaluate


def test_evaluate_counts_rows(tmp_path: Path):
    ds = tmp_path / "d.jsonl"
    ds.write_text('{"text":"a"}\n{"text":"bb"}\n', encoding="utf-8")
    r = evaluate(StubAdapter(), ds, timeout_s=1.0)
    assert r.total == 2
    assert r.ok == 2
    assert r.failed == 0
