from __future__ import annotations

import argparse
import json
import sys

from model_service.config import load_settings
from model_service.contracts import coerce_input
from model_service.eval.runner import StopConditions, evaluate, load_jsonl
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
    bad = 0
    for i, row in enumerate(rows, start=1):
        try:
            coerce_input(row)
        except Exception as e:  # noqa: BLE001
            bad += 1
            print(f"row {i}: invalid input ({type(e).__name__}): {e}", file=sys.stderr)
    if bad == 0:
        print("ok: dataset inputs conform to contract")
        return 0
    print(f"failed: {bad} row(s) violate the input contract", file=sys.stderr)
    return 2


def cmd_eval(args: argparse.Namespace) -> int:
    settings = load_settings()
    model = _get_adapter(settings.adapter)
    stop_conditions = (
        StopConditions(success_rate_lt=args.stop_success_rate)
        if args.stop_success_rate is not None
        else None
    )

    redactor = None
    if args.redact_traces:

        def _redact(data: dict) -> dict:
            redacted = dict(data)
            if "text" in redacted:
                redacted["text"] = "[redacted]"
            return redacted

        redactor = _redact

    report = evaluate(
        model,
        args.dataset,
        timeout_s=args.timeout_s or settings.default_timeout_s,
        concurrency=args.concurrency,
        burst_size=args.burst_size,
        stop_conditions=stop_conditions,
        redactor=redactor,
        html_summary_path=args.html_summary,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
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
    p_eval.add_argument("--concurrency", type=int, default=1)
    p_eval.add_argument("--burst-size", type=int, default=None)
    p_eval.add_argument("--stop-success-rate", type=float, default=None)
    p_eval.add_argument("--html-summary", type=str, default=None)
    p_eval.add_argument(
        "--redact-traces",
        action="store_true",
        help="Redact trace inputs (best-effort redaction of text field)",
    )
    p_eval.set_defaults(fn=cmd_eval)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
