import pytest
from unittest.mock import Mock, patch
from src.models.core import OpenAIInterface

@pytest.fixture
def openai_interface():
    return OpenAIInterface(
        api_key="test_api_key",
        base_url="https://api.openai.com/v1",
        model="gpt-3.5-turbo",
        translate_prompt="Translate to {target_language}",
        content_translate_prompt="Translate content to {target_language}",
        temperature=0.2,
        top_p=0.2,
        frequency_penalty=0,
        presence_penalty=0,
        max_tokens=2000,
        summary_prompt="Summarize in {target_language}"
    )

def test_client_property(openai_interface):
    client = openai_interface.client
    assert client.api_key == "test_api_key"
    assert client.base_url.host == "api.openai.com"
    assert client.timeout == 120.0

@patch.object(OpenAIInterface, 'client')
def test_validate_success(mock_openai, openai_interface):
    mock_response = Mock()
    mock_response.choices = [Mock(finish_reason="stop")]
    mock_openai.chat.completions.create.return_value = mock_response

    assert openai_interface.validate() == True

@patch.object(OpenAIInterface, 'client')
def test_validate_failure(mock_openai, openai_interface):
    mock_response = Mock()
    #mock_response.choices = []
    mock_openai.chat.completions.create.return_value = mock_response
    
    assert openai_interface.validate() == False
    #mock_response.chat.completions.create.assert_called_once()

@patch.object(OpenAIInterface, 'client')
def test_translate(mock_openai, openai_interface):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="翻译后的文本"))]
    mock_response.usage = Mock(total_tokens=50)
    mock_client.with_options().chat.completions.create.return_value = mock_response

    result = openai_interface.translate("Hello", "Chinese", text_type="title")
    assert result == {"text": "翻译后的文本", "tokens": 50}

@patch('openai.OpenAI')
def test_summarize(mock_openai, openai_interface):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="摘要内容"))]
    mock_response.usage = Mock(total_tokens=30)
    mock_client.with_options().chat.completions.create.return_value = mock_response

    result = openai_interface.summarize("Long text to summarize", "Chinese")
    assert result == {"text": "摘要内容", "tokens": 30}

def test_is_ai_property(openai_interface):
    assert openai_interface.is_ai == True

def test_polymorphic_identity(openai_interface):
    assert OpenAIInterface.__mapper_args__['polymorphic_identity'] == 'OpenAIInterface'

