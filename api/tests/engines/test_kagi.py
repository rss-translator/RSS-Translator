import pytest
from unittest.mock import patch, MagicMock
from api.models.engines.kagi import Kagi


@pytest.fixture
def kagi_translator():
    return Kagi(
        api_key="test_api_key",
        base_url="https://test.kagi.com/api/v0",
        title_translate_prompt="test_title_translate_prompt",
        content_translate_prompt="test_content_translate_prompt",
        summarization_engine="cecil",
        summary_type="summary",
    )


def test_init(kagi_translator):
    assert kagi_translator.api_key == "test_api_key"
    assert kagi_translator.base_url == "https://test.kagi.com/api/v0"
    assert kagi_translator.summarization_engine == "cecil"
    assert kagi_translator.summary_type == "summary"


def test_language_code_map():
    assert Kagi.language_code_map["English"] == "EN"
    assert Kagi.language_code_map["Chinese Simplified"] == "ZH"
    assert Kagi.language_code_map["Japanese"] == "JA"


@patch("api.models.engines.kagi.httpx.post")
def test_validate(mock_post, kagi_translator):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"output": "测试输出"}}
    mock_post.return_value = mock_response

    assert kagi_translator.validate() is True

    mock_post.assert_called_once_with(
        url="https://test.kagi.com/api/v0/fastgpt",
        headers={
            "content-type": "application/json",
            "Authorization": "Bot test_api_key",
        },
        data='{"query": "Hi"}',
        timeout=10,
    )


@patch("api.models.engines.kagi.httpx.post")
def test_translate(mock_post, kagi_translator):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"output": "你好", "tokens": 10}}
    mock_post.return_value = mock_response

    result = kagi_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "你好", "tokens": 10}
    mock_post.assert_called_once()


@patch("api.models.engines.kagi.httpx.post")
def test_summarize(mock_post, kagi_translator):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"output": "摘要", "tokens": 5}}
    mock_post.return_value = mock_response

    result = kagi_translator.summarize("这是一段长文本", "Chinese Simplified")

    assert result == {"text": "摘要", "tokens": 5}
    mock_post.assert_called_once_with(
        url="https://test.kagi.com/api/v0/summarize",
        headers={
            "content-type": "application/json",
            "Authorization": "Bot test_api_key",
        },
        data='{"text": "\\u8fd9\\u662f\\u4e00\\u6bb5\\u957f\\u6587\\u672c", "summary_type": "summary", "engine": "cecil", "target_language": "ZH"}',
        timeout=10,
    )


@patch("api.models.engines.kagi.logging")
@patch("api.models.engines.kagi.httpx.post")
def test_translate_exception(mock_post, mock_logging, kagi_translator):
    mock_post.side_effect = Exception("翻译错误")

    result = kagi_translator.translate("Hello", "Chinese Simplified")

    assert result == {"text": "", "tokens": 0}
    mock_logging.error.assert_called_once()


@patch("api.models.engines.kagi.logging")
def test_summarize_unsupported_language(mock_logging, kagi_translator):
    result = kagi_translator.summarize("This is a long text", "Unsupported Language")

    assert result == {"text": "", "tokens": 0}
    mock_logging.error.assert_called_once()
