from __future__ import annotations

from fastapi import Depends, FastAPI

from model_service.config import Settings, load_settings
from model_service.contracts import InputContract, OutputContract
from model_service.service.adapters import get_adapter
from model_service.service.pipeline import run


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="model-service")

    def get_settings() -> Settings:
        return settings

    def get_model(settings: Settings = Depends(get_settings)):
        return get_adapter(settings.adapter)

    def get_timeout(settings: Settings = Depends(get_settings)) -> float:
        return settings.default_timeout_s

    @app.get("/healthz")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/readyz")
    def readiness() -> dict[str, bool]:
        # Mirror health for now; expand when dependencies are added.
        return {"ok": True}

    @app.post("/v1/predict", response_model=OutputContract)
    def predict(
        payload: InputContract,
        model=Depends(get_model),
        timeout_s: float = Depends(get_timeout),
    ) -> OutputContract:
        return run(model, payload, timeout_s=timeout_s)

    return app
