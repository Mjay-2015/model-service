from pathlib import Path
import pytest

from model_service.model.stub import StubAdapter
from model_service.eval.runner import DatasetQualityReport, evaluate, load_jsonl, validate_dataset


def test_evaluate_counts_rows(tmp_path: Path):
    ds = tmp_path / "d.jsonl"
    ds.write_text(
        '{"text":"a","language":"en","metadata":{"id":"1","source":"t"}}\n'
        '{"text":"bb","language":"en","metadata":{"id":"2","source":"t"}}\n',
        encoding="utf-8",
    )
    r = evaluate(StubAdapter(), ds, timeout_s=1.0)
    assert r.total == 2
    assert r.ok == 2
    assert r.failed == 0


def test_validate_dataset_reports_schema_version_errors(tmp_path: Path):
    ds = tmp_path / "bad.jsonl"
    ds.write_text(
        '{"schema_version":"0.9","text":"a","language":"en","metadata":{"id":"1","source":"t"}}\n', encoding="utf-8"
    )
    rows = load_jsonl(ds)
    report = validate_dataset(rows)
    assert isinstance(report, DatasetQualityReport)
    assert report.total_rows == 1
    assert report.invalid_rows == 1
    assert report.schema_version_errors == 1


def test_evaluate_rejects_invalid_dataset(tmp_path: Path):
    ds = tmp_path / "bad.jsonl"
    ds.write_text('{"text":"hola","language":"es","metadata":{"id":"1","source":"t"}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="dataset failed quality checks"):
        evaluate(StubAdapter(), ds, timeout_s=1.0)
