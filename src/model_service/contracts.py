from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

INPUT_SCHEMA_VERSION = "1.0"
OUTPUT_SCHEMA_VERSION = "1.0"
LANGUAGE_WHITELIST: frozenset[str] = frozenset({"en"})
REQUIRED_METADATA_KEYS: frozenset[str] = frozenset({"id", "source"})


class InputContract(BaseModel):
    SCHEMA_VERSION: str = INPUT_SCHEMA_VERSION

    schema_version: str = Field(default=INPUT_SCHEMA_VERSION)
    text: str = Field(min_length=1, max_length=10_000)
    language: str = Field(default="en", description="BCP-47 language code")
    metadata: dict[str, str] = Field(default_factory=lambda: {"id": "unknown", "source": "unspecified"})

    @field_validator("schema_version")
    @classmethod
    def _enforce_schema_version(cls, v: str) -> str:  # noqa: D417 (pydantic)
        if v != INPUT_SCHEMA_VERSION:
            raise ValueError(f"input schema_version mismatch: expected {INPUT_SCHEMA_VERSION}, got {v}")
        return v

    @field_validator("language")
    @classmethod
    def _validate_language(cls, v: str) -> str:  # noqa: D417 (pydantic)
        if v not in LANGUAGE_WHITELIST:
            allowed = ", ".join(sorted(LANGUAGE_WHITELIST))
            raise ValueError(f"language must be one of: {allowed}")
        return v

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, v: dict[str, str]) -> dict[str, str]:  # noqa: D417 (pydantic)
        missing = REQUIRED_METADATA_KEYS.difference(v)
        if missing:
            raise ValueError(f"metadata missing required keys: {sorted(missing)}")
        return v


class OutputContract(BaseModel):
    SCHEMA_VERSION: str = OUTPUT_SCHEMA_VERSION

    schema_version: str = Field(default=OUTPUT_SCHEMA_VERSION)
    ok: bool = True
    model_version: str
    output_text: str
    score: float | None = None
    error: str | None = None
    latency_ms: float | None = None

    @field_validator("schema_version")
    @classmethod
    def _enforce_schema_version(cls, v: str) -> str:  # noqa: D417 (pydantic)
        if v != OUTPUT_SCHEMA_VERSION:
            raise ValueError(f"output schema_version mismatch: expected {OUTPUT_SCHEMA_VERSION}, got {v}")
        return v


def coerce_input(data: dict) -> InputContract:
    # Raises pydantic.ValidationError if invalid (good)
    return InputContract.model_validate(data)


def coerce_output(data: dict) -> OutputContract:
    return OutputContract.model_validate(data)
