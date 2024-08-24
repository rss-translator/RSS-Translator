import pytest
from unittest.mock import patch, MagicMock
from src.models.translators.google_translate_web import GoogleTranslateWeb

@pytest.fixture
def google_translate_web():
    return GoogleTranslateWeb(max_characters=5000, interval=5)

def test_init(google_translate_web):
    assert hasattr(google_translate_web, 'ts')

def test_language_code_map():
    assert GoogleTranslateWeb.language_code_map["English"] == "en"
    assert GoogleTranslateWeb.language_code_map["Chinese Simplified"] == "zh-CN"

@patch('src.models.translators.google_translate_web.GoogleTranslateWeb.translate')
def test_validate(mock_translate, google_translate_web):
    mock_translate.return_value = {"text": "你好", "characters": 2}
    assert google_translate_web.validate() == True

    mock_translate.return_value = {"text": "", "characters": 2}
    assert google_translate_web.validate() == False

@patch('src.models.translators.google_translate_web.sleep')
def test_translate(mock_sleep, google_translate_web):
    google_translate_web.ts = MagicMock()
    google_translate_web.ts.translate_text.return_value = "你好"
    
    result = google_translate_web.translate("hello", "Chinese Simplified")
    
    assert result == {"text": "你好", "characters": 5}
    google_translate_web.ts.translate_text.assert_called_once_with(
        "hello", 
        to_language="zh-CN", 
        translator="google", 
        reset_host_url=None, 
        proxies=None
    )
    mock_sleep.assert_called_once_with(5)

def test_translate_unsupported_language(google_translate_web):
    result = google_translate_web.translate("hello", "Unsupported Language")
    assert result == {"text": "", "characters": 5}

@patch('src.models.translators.google_translate_web.logging')
def test_translate_exception(mock_logging, google_translate_web):
    google_translate_web.ts = MagicMock()
    google_translate_web.ts.translate_text.side_effect = Exception("Translation error")
    
    result = google_translate_web.translate("hello", "Chinese Simplified")
    
    assert result == {"text": "", "characters": 5}
    mock_logging.error.assert_called_once()