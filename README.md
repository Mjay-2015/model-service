# model-service

A production-oriented CLI template for integrating and evaluating ML models inside a software service.

I care about software that's easier to build, change, and reason about.

## Why
Most ML examples focus on the model.
This repo focuses on the system around the model: contracts, failure modes,
evaluation, and maintainability.

When a model becomes a dependency, the surrounding software still needs to be:
- predictable under change
- safe under failure
- easy to reason about

## What this repo includes
- A model adapter interface (the model is swappable)
- Explicit contracts for model inputs and outputs
- A small evaluation runner suitable for CI
- Safe fallback behavior when models fail
- Tests for the boring parts (where incidents usually come from)

## Architecture (high level)

```
input
|
v
contracts --> pipeline --> model adapter
|
+-- validation
+-- timeout / error handling
+-- fallback
|
v
contract-valid output
```

## Quickstart
Requires Python 3.11+

Install:
- `pip install -e ".[dev]"`

Run a single prediction:
- `model-service predict --text "hello world"`

Validate a dataset:
- `model-service validate --dataset src/model_service/eval/datasets/tiny.jsonl`

Run evaluation:
- `model-service eval --dataset src/model_service/eval/datasets/tiny.jsonl`

## Principles
- The system is the product
- Explicit contracts beat implicit assumptions
- Make failure modes boring
- Optimize for change

For design rationale, see [`DESIGN.md`](DESIGN.md).
