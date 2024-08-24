import pytest
from unittest.mock import patch, MagicMock
from src.models.translators.openl import Openl

@pytest.fixture
def openl_translator():
    return Openl(
        api_key="apikey",
        base_url="https://api.openl.club",
        service_name="deepl",
        max_characters=5000
    )

def test_init(openl_translator):
    assert openl_translator.api_key == "apikey"
    assert openl_translator.base_url == "https://api.openl.club"
    assert openl_translator.service_name == "deepl"
    assert openl_translator.max_characters == 5000

def test_language_code_map():
    assert Openl.language_code_map["English"] == "en"
    assert Openl.language_code_map["Chinese Simplified"] == "zh"
    assert Openl.language_code_map["Japanese"] == "ja"

@patch("src.models.translators.openl.httpx.post")
def test_validate(mock_post, openl_translator):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": True}
    mock_post.return_value = mock_response

    assert openl_translator.validate() is True

    mock_post.assert_called_once_with(
        url=openl_translator.base_url + "/user/info",
        headers={"content-type": "application/json"},
        data='{"apikey": "apikey"}',
        timeout=10
    )

@patch("src.models.translators.openl.httpx.post")
def test_translate(mock_post, openl_translator):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": True, "result": "你好"}
    mock_post.return_value = mock_response

    result = openl_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "你好", "characters": 5}
    mock_post.assert_called_once_with(
        url=openl_translator.base_url + "/services/deepl/translate",
        headers={"content-type": "application/json"},
        data='{"apikey": "apikey", "text": "Hello", "target_lang": "zh"}',
        timeout=10
    )

def test_translate_unsupported_language(openl_translator):
    result = openl_translator.translate("Hello", "Unsupported Language")
    assert result == {"text": "", "characters": 5}

@patch("src.models.translators.openl.logging")
@patch("src.models.translators.openl.httpx.post")
def test_translate_exception(mock_post, mock_logging, openl_translator):
    mock_post.side_effect = Exception("翻译错误")

    result = openl_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "", "characters": 5}
    mock_logging.error.assert_called_once()
