import pytest
from unittest.mock import patch
from src.models.translators.dev import Test

@pytest.fixture
def test_instance():
    return Test(translated_text="@@Translated Text@@", interval=5)

def test_validate(test_instance):
    assert test_instance.validate() == True

@patch('src.models.translators.dev.sleep')
def test_translate(mock_sleep, test_instance):
    text = "Hello, world!"
    target_language = "fr"
    
    result = test_instance.translate(text, target_language)
    
    assert result["text"] == "@@Translated Text@@"
    assert result["tokens"] == 0
    assert result["characters"] == len(text)
    mock_sleep.assert_called_once_with(test_instance.interval)

@patch('src.models.translators.dev.Test.translate')
def test_summarize(mock_translate, test_instance):
    text = "This is a test text."
    target_language = "es"
    
    test_instance.summarize(text, target_language)
    
    mock_translate.assert_called_once_with(text, target_language)