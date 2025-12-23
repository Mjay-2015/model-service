from __future__ import annotations

from typing import Protocol

from model_service.contracts import InputContract, OutputContract


class ModelAdapter(Protocol):
    @property
    def model_version(self) -> str: ...

    def predict(self, x: InputContract) -> OutputContract: ...
