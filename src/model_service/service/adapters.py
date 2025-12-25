from __future__ import annotations

from model_service.model.base import ModelAdapter
from model_service.model.stub import StubAdapter


def get_adapter(name: str) -> ModelAdapter:
    if name == "stub":
        return StubAdapter()
    raise ValueError(f"Unknown adapter: {name!r}")
