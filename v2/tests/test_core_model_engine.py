import pytest
from unittest.mock import Mock, patch
from ..models.core import Engine, OpenAIInterface

def test_engine_min_size():
    engine = Engine()
    engine.max_characters = 1000
    assert engine.min_size() == 700

def test_engine_max_size():
    engine = Engine()
    engine.max_tokens = 1000
    assert engine.max_size() == 900

def test_engine_translate_not_implemented():
    engine = Engine()
    with pytest.raises(NotImplementedError):
        engine.translate("test", "zh")

def test_engine_validate_not_implemented():
    engine = Engine()
    with pytest.raises(NotImplementedError):
        engine.validate()