from __future__ import annotations

import argparse
import json
import sys

from model_service.config import load_settings
from model_service.contracts import coerce_input
from model_service.eval.runner import DatasetQualityReport, evaluate, load_jsonl, validate_dataset
from model_service.model.stub import StubAdapter
from model_service.service.pipeline import run


def _get_adapter(name: str):
    # Expand later: hosted adapter, local model adapter, etc.
    if name == "stub":
        return StubAdapter()
    raise SystemExit(f"Unknown adapter: {name!r}")


def cmd_predict(args: argparse.Namespace) -> int:
    settings = load_settings()
    model = _get_adapter(settings.adapter)
    x = coerce_input({"text": args.text})
    y = run(model, x, timeout_s=args.timeout_s or settings.default_timeout_s)
    print(json.dumps(y.model_dump(), ensure_ascii=False))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    rows = load_jsonl(args.dataset)
    report = validate_dataset(rows)
    _print_quality_report(report)
    if report.invalid_rows == 0:
        return 0
    return 2


def cmd_eval(args: argparse.Namespace) -> int:
    settings = load_settings()
    model = _get_adapter(settings.adapter)
    report = evaluate(model, args.dataset, timeout_s=args.timeout_s or settings.default_timeout_s)
    print(json.dumps(report.__dict__, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="model-service", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_pred = sub.add_parser("predict", help="Run a single prediction")
    p_pred.add_argument("--text", required=True)
    p_pred.add_argument("--timeout-s", type=float, default=None)
    p_pred.set_defaults(fn=cmd_predict)

    p_val = sub.add_parser("validate", help="Validate a dataset against the input contract")
    p_val.add_argument("--dataset", required=True)
    p_val.set_defaults(fn=cmd_validate)

    p_eval = sub.add_parser("eval", help="Run evaluation over a dataset")
    p_eval.add_argument("--dataset", required=True)
    p_eval.add_argument("--timeout-s", type=float, default=None)
    p_eval.set_defaults(fn=cmd_eval)

    return p


def _print_quality_report(report: DatasetQualityReport) -> None:
    summary = {
        "total_rows": report.total_rows,
        "valid_rows": report.valid_rows,
        "invalid_rows": report.invalid_rows,
        "schema_version_errors": report.schema_version_errors,
        "language_errors": report.language_errors,
        "metadata_errors": report.metadata_errors,
    }
    print(json.dumps({"dataset_quality": summary}, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
