import pytest
from unittest.mock import Mock, patch
from rsstranslator.backend.models.core import OpenAIInterface

@pytest.fixture
def openai_interface():
    return OpenAIInterface(
        api_key="test_api_key",
        base_url="https://api.openai.com/v1",
        model="gpt-3.5-turbo",
        title_translate_prompt="Translate to {target_language}",
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

@patch('rsstranslator.backend.models.core.OpenAI')
def test_validate_success(mock_openai, openai_interface):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_response = Mock()
    mock_response.choices = [Mock(finish_reason="stop")]
    mock_client.with_options.return_value.chat.completions.create.return_value = mock_response

    assert openai_interface.validate() is True
    mock_client.with_options.assert_called_once_with(max_retries=3)
    # mock_client.with_options.return_value.chat.completions.create.assert_called_once_with(
    #     model=openai_interface.model,
    #     messages=[{"role": "user", "content": "Hi"}],
    #     max_tokens=10
    # )

@patch('rsstranslator.backend.models.core.OpenAI')
def test_validate_failure(mock_openai, openai_interface):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.with_options.return_value.chat.completions.create.side_effect = Exception("API Error")

    assert openai_interface.validate() is False
    mock_client.with_options.assert_called_once_with(max_retries=3)

@patch('rsstranslator.backend.models.core.OpenAI')
def test_translate(mock_openai, openai_interface):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="翻译后的文本"))]
    mock_response.usage = Mock(total_tokens=50)
    mock_client.with_options.return_value.chat.completions.create.return_value = mock_response

    result = openai_interface.translate("Hello", "中文")

    assert result == {"text": "翻译后的文本", "tokens": 50}
    mock_client.with_options.assert_called_once_with(max_retries=3)
    mock_client.with_options.return_value.chat.completions.create.assert_called_once()

@patch('rsstranslator.backend.models.core.OpenAI')
def test_summarize(mock_openai, openai_interface):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="摘要内容"))]
    mock_response.usage = Mock(total_tokens=30)
    mock_client.with_options.return_value.chat.completions.create.return_value = mock_response

    result = openai_interface.summarize("这是一段长文本", "中文")

    assert result == {"text": "摘要内容", "tokens": 30}
    mock_client.with_options.assert_called_once_with(max_retries=3)
    mock_client.with_options.return_value.chat.completions.create.assert_called_once()

def test_openai_interface_database_operations():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from rsstranslator.backend.models.core import Base, OpenAIInterface

    # 创建内存数据库
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    
    # 创建会话
    session = Session()

    # 测试写入操作
    new_interface = OpenAIInterface(
        name="测试OpenAI接口",
        api_key="test_api_key",
        model="gpt-3.5-turbo",
        is_available=True
    )
    session.add(new_interface)
    session.commit()

    # 测试读取操作
    queried_interface = session.query(OpenAIInterface).filter_by(name="测试OpenAI接口").first()
    assert queried_interface is not None
    assert queried_interface.name == "测试OpenAI接口"
    assert queried_interface.api_key == "test_api_key"
    assert queried_interface.model == "gpt-3.5-turbo"
    assert queried_interface.is_available is True
    assert queried_interface.is_ai is True

    # 测试更新操作
    queried_interface.model = "gpt-4"
    session.commit()
    updated_interface = session.query(OpenAIInterface).filter_by(name="测试OpenAI接口").first()
    assert updated_interface.model == "gpt-4"

    # 测试删除操作
    session.delete(queried_interface)
    session.commit()
    deleted_interface = session.query(OpenAIInterface).filter_by(name="测试OpenAI接口").first()
    assert deleted_interface is None

    # 关闭会话
    session.close()
