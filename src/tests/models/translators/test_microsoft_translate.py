import pytest
from unittest.mock import patch, MagicMock
from src.models.translators.microsoft_translate import MicrosoftTranslator

@pytest.fixture
def microsoft_translator():
    return MicrosoftTranslator(
        api_key="测试_api_key",
        location="eastus",
        endpoint="https://api.cognitive.microsofttranslator.com",
        max_characters=5000
    )

def test_init(microsoft_translator):
    assert microsoft_translator.api_key == "测试_api_key"
    assert microsoft_translator.location == "eastus"
    assert microsoft_translator.endpoint == "https://api.cognitive.microsofttranslator.com"
    assert microsoft_translator.max_characters == 5000

def test_language_code_map():
    assert MicrosoftTranslator.language_code_map["English"] == "en"
    assert MicrosoftTranslator.language_code_map["Chinese Simplified"] == "zh-Hans"
    assert MicrosoftTranslator.language_code_map["Japanese"] == "ja"

@patch("src.models.translators.microsoft_translate.MicrosoftTranslator.translate")
def test_validate(mock_translate, microsoft_translator):
    mock_translate.return_value = {"text": "你好", "characters": 2}
    assert microsoft_translator.validate() == True

    mock_translate.return_value = {"text": "", "characters": 2}
    assert microsoft_translator.validate() == False

@patch("src.models.translators.microsoft_translate.httpx.Client")
def test_translate(mock_client, microsoft_translator):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [{"translations": [{"text": "你好"}]}]
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response

    result = microsoft_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "你好", "characters": 5}
    mock_client.return_value.__enter__.return_value.post.assert_called_once()

def test_translate_unsupported_language(microsoft_translator):
    result = microsoft_translator.translate("Hello", "Unsupported Language")
    assert result == {"text": "", "characters": 5}

@patch("src.models.translators.microsoft_translate.logging")
@patch("src.models.translators.microsoft_translate.httpx.Client")
def test_translate_exception(mock_client, mock_logging, microsoft_translator):
    mock_client.return_value.__enter__.return_value.post.side_effect = Exception("翻译错误")

    result = microsoft_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "", "characters": 5}
    mock_logging.error.assert_called_once()
