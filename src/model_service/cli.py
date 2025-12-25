from __future__ import annotations

import argparse
import json
import sys

from model_service.config import load_settings
from model_service.contracts import coerce_input
from model_service.eval.runner import evaluate, load_jsonl
from model_service.service.pipeline import run
from model_service.service.adapters import get_adapter


def cmd_predict(args: argparse.Namespace) -> int:
    settings = load_settings()
    try:
        model = get_adapter(settings.adapter)
    except ValueError as e:
        raise SystemExit(str(e))
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
    try:
        model = get_adapter(settings.adapter)
    except ValueError as e:
        raise SystemExit(str(e))
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
