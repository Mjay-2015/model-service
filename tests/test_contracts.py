import pytest
from model_service.contracts import coerce_input


def test_input_contract_accepts_text():
    x = coerce_input({"text": "hi"})
    assert x.text == "hi"


def test_input_contract_rejects_empty_text():
    with pytest.raises(Exception):
        coerce_input({"text": ""})
