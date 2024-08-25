# 文件名: test_deepl.py

import pytest
from unittest.mock import patch, MagicMock
from rsstranslator.backend.models.translators.deepl import DeepL

@pytest.fixture
def deepl_instance():
    return DeepL(api_key='test_key')

# 测试validate方法
@patch('rsstranslator.backend.models.translators.deepl.deepl.Translator')
def test_validate_success(mock_translator, deepl_instance):
    mock_client = MagicMock()
    mock_usage = MagicMock()
    mock_usage.character.valid = True
    mock_client.get_usage.return_value = mock_usage
    mock_translator.return_value = mock_client
    
    assert deepl_instance.validate() is True

@patch('rsstranslator.backend.models.translators.deepl.deepl.Translator')
def test_validate_failure(mock_translator, deepl_instance):
    mock_client = MagicMock()
    mock_client.get_usage.side_effect = Exception('API Error')
    mock_translator.return_value = mock_client
    
    assert deepl_instance.validate() is False

# 测试translate方法
@patch('rsstranslator.backend.models.translators.deepl.deepl.Translator')
def test_translate_success(mock_translator, deepl_instance):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '翻译后的文本'
    mock_client.translate_text.return_value = mock_response
    mock_translator.return_value = mock_client
    
    result = deepl_instance.translate('Hello', 'Chinese Simplified')
    assert result['text'] == '翻译后的文本'
    assert result['characters'] == 5

@patch('rsstranslator.backend.models.translators.deepl.deepl.Translator')
def test_translate_unsupported_language(mock_translator, deepl_instance):
    mock_client = MagicMock()
    mock_translator.return_value = mock_client
    
    result = deepl_instance.translate('Hello', 'Unsupported Language')
    assert result['text'] == ''
    assert result['characters'] == 5

@patch('rsstranslator.backend.models.translators.deepl.deepl.Translator')
def test_translate_api_error(mock_translator, deepl_instance):
    mock_client = MagicMock()
    mock_client.translate_text.side_effect = Exception('API Error')
    mock_translator.return_value = mock_client
    
    result = deepl_instance.translate('Hello', 'Chinese Simplified')
    assert result['text'] == ''
    assert result['characters'] == 5

# 测试language_code_map
def test_language_code_map(deepl_instance):
    assert deepl_instance.language_code_map['English'] == 'EN-US'
    assert deepl_instance.language_code_map['Chinese Simplified'] == 'ZH'
    assert deepl_instance.language_code_map['Russian'] == 'RU'
    # 可以继续添加其他语言的测试