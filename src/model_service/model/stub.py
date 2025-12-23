from __future__ import annotations

import time
from model_service.contracts import InputContract, OutputContract


class StubAdapter:
    """
    Intentionally boring: deterministic, fast, and test-friendly.
    Swap this with a real adapter later.
    """

    @property
    def model_version(self) -> str:
        return "stub-1"

    def predict(self, x: InputContract) -> OutputContract:
        # Simulate tiny work
        time.sleep(0.01)
        # "Inference": reverse + pretend score
        out = x.text[::-1]
        score = min(1.0, len(x.text) / 100.0)
        return OutputContract(model_version=self.model_version, output_text=out, score=score)
