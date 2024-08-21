import pytest
from unittest.mock import Mock, patch
from src.models.translators.caiyun import CaiYun

@pytest.fixture
def caiyun_translator():
    return CaiYun(
        api_key="test_token",
        base_url="http://test.api.caiyunapp.com/v1/translator",
        max_characters=5000
    )

def test_language_code_map(caiyun_translator):
    assert caiyun_translator.language_code_map["English"] == "en"
    assert caiyun_translator.language_code_map["Chinese Simplified"] == "zh"
    assert caiyun_translator.language_code_map["Japanese"] == "ja"

@patch('httpx.post')
def test_validate_success(mock_post, caiyun_translator):
    mock_response = Mock()
    mock_response.json.return_value = {"target": "你好"}
    mock_post.return_value = mock_response

    assert caiyun_translator.validate() is True
    mock_post.assert_called_once()

@patch('httpx.post')
def test_validate_failure(mock_post, caiyun_translator):
    mock_post.side_effect = Exception("API Error")

    assert caiyun_translator.validate() is False
    mock_post.assert_called_once()

@patch('httpx.post')
def test_translate_success(mock_post, caiyun_translator):
    mock_response = Mock()
    mock_response.json.return_value = {"target": "你好"}
    mock_post.return_value = mock_response

    result = caiyun_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "你好", "characters": 5}
    mock_post.assert_called_once()

@patch('httpx.post')
def test_translate_unsupported_language(mock_post, caiyun_translator):
    result = caiyun_translator.translate("Hello", "Unsupported Language")

    assert result == {"text": "", "characters": 5}
    mock_post.assert_not_called()

@patch('httpx.post')
def test_translate_api_error(mock_post, caiyun_translator):
    mock_post.side_effect = Exception("API Error")

    result = caiyun_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "", "characters": 5}
    mock_post.assert_called_once()
