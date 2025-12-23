from model_service.contracts import InputContract
from model_service.service.pipeline import run


class BoomAdapter:
    @property
    def model_version(self) -> str:
        return "boom-1"

    def predict(self, x: InputContract):
        raise RuntimeError("kaboom")


def test_pipeline_falls_back_on_error():
    x = InputContract(text="hello")
    y = run(BoomAdapter(), x, timeout_s=1.0)
    assert y.ok is False
    assert "RuntimeError" in (y.error or "")
    assert y.output_text == ""
    assert y.model_version == "boom-1"
