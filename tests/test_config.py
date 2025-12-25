from model_service.config import AdapterRuntimeSettings, load_settings


def test_adapter_settings_env_parses_overrides(monkeypatch):
    env_payload = (
        '{"stub":{"max_concurrency":3,"rate_limit_per_second":2.5,'
        '"retry_attempts":4,"retry_backoff_base_s":0.2,"retry_jitter_s":0.1},"bad":"oops"}'
    )
    monkeypatch.setenv("MODEL_SERVICE_ADAPTER_SETTINGS", env_payload)
    settings = load_settings()
    stub_cfg = settings.adapter_overrides["stub"]
    assert stub_cfg == AdapterRuntimeSettings(
        max_concurrency=3,
        rate_limit_per_second=2.5,
        retry_attempts=4,
        retry_backoff_base_s=0.2,
        retry_jitter_s=0.1,
    )


def test_adapter_settings_env_defaults_on_invalid(monkeypatch):
    monkeypatch.setenv("MODEL_SERVICE_ADAPTER_SETTINGS", "not-json")
    settings = load_settings()
    assert settings.adapter_overrides == {}


def test_default_timeout_invalid_env_uses_default(monkeypatch):
    monkeypatch.setenv("MODEL_SERVICE_TIMEOUT_S", "nope")
    settings = load_settings()
    assert settings.default_timeout_s == 2.0


def test_default_timeout_non_positive_env_uses_default(monkeypatch):
    monkeypatch.setenv("MODEL_SERVICE_TIMEOUT_S", "0")
    settings = load_settings()
    assert settings.default_timeout_s == 2.0
