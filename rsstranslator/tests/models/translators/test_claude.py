import pytest
from unittest.mock import patch, MagicMock
from rsstranslator.backend.models.translators.claude import Claude

@pytest.fixture
def claude_instance():
    return Claude(
        api_key="test_api_key",
        model="claude-3-haiku-20240307",
        base_url="https://api.anthropic.com",
        title_translate_prompt="翻译成{target_language}",
        content_translate_prompt="翻译内容为{target_language}",
        temperature=0.7,
        top_p=0.7,
        max_tokens=1000
    )

@pytest.mark.parametrize("api_response,expected_result", [
    ([MagicMock(type="text", text="你好")], True),
    (Exception("API错误"), False)
])
@patch('anthropic.Anthropic')
def test_validate(mock_anthropic, claude_instance, api_response, expected_result):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    
    if isinstance(api_response, Exception):
        mock_client.messages.create.side_effect = api_response
    else:
        mock_client.messages.create.return_value.content = api_response

    result = claude_instance.validate()
    assert result == expected_result

@pytest.mark.parametrize("input_text,target_lang,api_response,expected_output", [
    ("Hello", "中文", [MagicMock(type="text", text="你好")], {"text": "你好", "tokens": 10}),
    ("Hello", "中文", Exception("API错误"), {"text": "", "tokens": 10})
])
@patch('anthropic.Anthropic')
def test_translate(mock_anthropic, claude_instance, input_text, target_lang, api_response, expected_output):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.count_tokens.return_value = 10
    
    if isinstance(api_response, Exception):
        mock_client.messages.create.side_effect = api_response
    else:
        mock_client.messages.create.return_value.content = api_response
        mock_client.messages.create.return_value.usage.input_tokens = 5
        mock_client.messages.create.return_value.usage.output_tokens = 5

    result = claude_instance.translate(input_text, target_lang)
    assert result == expected_output

@patch('anthropic.Anthropic')
def test_summarize(mock_anthropic, claude_instance):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.count_tokens.return_value = 20
    mock_client.messages.create.return_value.content = [MagicMock(type="text", text="摘要")]
    mock_client.messages.create.return_value.usage.input_tokens = 10
    mock_client.messages.create.return_value.usage.output_tokens = 10

    claude_instance.summary_prompt = "总结为{target_language}"
    result = claude_instance.summarize("这是一段长文本", "中文")
    assert result == {"text": "摘要", "tokens": 20}

