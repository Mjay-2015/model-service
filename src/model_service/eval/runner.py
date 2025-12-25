from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from model_service.contracts import (
    INPUT_SCHEMA_VERSION,
    LANGUAGE_WHITELIST,
    REQUIRED_METADATA_KEYS,
    coerce_input,
)
from model_service.model.base import ModelAdapter
from model_service.service.pipeline import run


@dataclass(frozen=True)
class EvalReport:
    total: int
    ok: int
    failed: int
    p50_ms: float
    p95_ms: float


@dataclass(frozen=True)
class DatasetQualityReport:
    total_rows: int
    valid_rows: int
    invalid_rows: int
    schema_version_errors: int
    language_errors: int
    metadata_errors: int

    def as_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "schema_version_errors": self.schema_version_errors,
            "language_errors": self.language_errors,
            "metadata_errors": self.metadata_errors,
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


def validate_dataset(rows: list[dict]) -> DatasetQualityReport:
    schema_version_errors = 0
    language_errors = 0
    metadata_errors = 0
    valid_rows = 0

    for row in rows:
        # Required metadata/language presence checks before schema validation
        row_invalid = False
        lang = row.get("language")
        if lang is None or lang not in LANGUAGE_WHITELIST:
            language_errors += 1
            row_invalid = True

        metadata = row.get("metadata")
        if not isinstance(metadata, dict) or REQUIRED_METADATA_KEYS.difference(metadata):
            metadata_errors += 1
            row_invalid = True

        if row_invalid:
            continue

        try:
            coerce_input(row)
            valid_rows += 1
        except ValidationError as e:
            for err in e.errors():
                if err.get("loc") == ("schema_version",):
                    schema_version_errors += 1
                elif err.get("loc") == ("language",):
                    language_errors += 1
                elif err.get("loc") == ("metadata",):
                    metadata_errors += 1
            # If we miss specific categorization, still count the row as invalid
        except Exception:
            # Non-ValidationError should still count as invalid
            pass

    total_rows = len(rows)
    invalid_rows = total_rows - valid_rows
    return DatasetQualityReport(
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        schema_version_errors=schema_version_errors,
        language_errors=language_errors,
        metadata_errors=metadata_errors,
    )


def evaluate(model: ModelAdapter, dataset_path: str | Path, timeout_s: float) -> EvalReport:
    rows = load_jsonl(dataset_path)
    quality_report = validate_dataset(rows)
    if quality_report.invalid_rows:
        raise ValueError(
            "dataset failed quality checks: "
            f"{quality_report.invalid_rows} invalid of {quality_report.total_rows} "
            f"(schema_version_errors={quality_report.schema_version_errors}, "
            f"language_errors={quality_report.language_errors}, "
            f"metadata_errors={quality_report.metadata_errors}, "
            f"expected_schema_version={INPUT_SCHEMA_VERSION})"
        )
    latencies: list[float] = []
    ok = 0
    failed = 0

    for row in rows:
        x = coerce_input(row)
        y = run(model, x, timeout_s=timeout_s)
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
