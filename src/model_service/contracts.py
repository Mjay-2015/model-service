from __future__ import annotations

from pydantic import BaseModel, Field


class InputContract(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class OutputContract(BaseModel):
    ok: bool = True
    model_version: str
    output_text: str
    score: float | None = None
    error: str | None = None
    latency_ms: float | None = None


def coerce_input(data: dict) -> InputContract:
    # Raises pydantic.ValidationError if invalid (good)
    return InputContract.model_validate(data)


def coerce_output(data: dict) -> OutputContract:
    return OutputContract.model_validate(data)
