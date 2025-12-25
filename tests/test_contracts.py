import pytest
from pydantic import ValidationError

from model_service.contracts import (
    INPUT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    OutputContract,
    coerce_input,
    coerce_output,
)


def test_input_contract_accepts_text():
    x = coerce_input({"text": "hi"})
    assert x.text == "hi"
    assert x.schema_version == INPUT_SCHEMA_VERSION
    assert x.language == "en"
    assert x.metadata["id"]
    assert x.metadata["source"]


def test_input_contract_rejects_empty_text():
    with pytest.raises(Exception):
        coerce_input({"text": ""})


def test_input_contract_rejects_bad_schema_version():
    with pytest.raises(ValidationError):
        coerce_input({"text": "hello", "schema_version": "0.9", "language": "en", "metadata": {"id": "1", "source": "s"}})


def test_input_contract_rejects_bad_language():
    with pytest.raises(ValidationError):
        coerce_input({"text": "hello", "language": "fr", "metadata": {"id": "1", "source": "s"}})


def test_input_contract_requires_metadata_keys():
    with pytest.raises(ValidationError):
        coerce_input({"text": "hello", "language": "en", "metadata": {"id": "1"}})


def test_output_contract_schema_version_enforced():
    y = coerce_output({"model_version": "stub", "output_text": "ok"})
    assert y.schema_version == OUTPUT_SCHEMA_VERSION
    with pytest.raises(ValidationError):
        OutputContract.model_validate({"schema_version": "0.9", "model_version": "stub", "output_text": "ok"})
