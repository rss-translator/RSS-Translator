import pytest
from api.models.engines.free_translators import FreeTranslators

def test_free_translators_init():
    free_translators = FreeTranslators(max_characters=3000, interval=5)
    assert free_translators.proxy is None
    assert free_translators.max_characters == 3000
    assert free_translators.interval == 5

def test_free_translators_client():
    free_translators = FreeTranslators()
    client = free_translators.client
    assert client is not None

def test_free_translators_translate():
    free_translators = FreeTranslators()
    text = "Hello, World!"
    target_language = "Chinese Simplified"
    result = free_translators.translate(text, target_language)
    assert "世界" in result['text']

def test_free_translators_validate():
    free_translators = FreeTranslators()
    assert free_translators.validate() is True