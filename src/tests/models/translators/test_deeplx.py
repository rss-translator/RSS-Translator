import pytest
from unittest.mock import patch, Mock
from src.models.translators.deeplx import DeepLX

class TestDeepLX:
    @pytest.fixture
    def deeplx_instance(self):
        return DeepLX()

    def test_language_code_map(self, deeplx_instance):
        assert deeplx_instance.language_code_map["English"] == "EN"
        assert deeplx_instance.language_code_map["Chinese Simplified"] == "ZH"
        assert deeplx_instance.language_code_map["Russian"] == "RU"

    @patch('httpx.post')
    def test_validate_success(self, mock_post, deeplx_instance):
        mock_response = Mock()
        mock_response.json.return_value = {"data": "你好世界"}
        mock_post.return_value = mock_response
        
        assert deeplx_instance.validate() == True

    @patch('httpx.post')
    def test_validate_failure(self, mock_post, deeplx_instance):
        mock_post.side_effect = Exception("Connection error")
        
        assert deeplx_instance.validate() == False

    @patch('httpx.post')
    def test_translate_success(self, mock_post, deeplx_instance):
        mock_response = Mock()
        mock_response.json.return_value = {"data": "你好世界"}
        mock_post.return_value = mock_response
        
        result = deeplx_instance.translate("Hello World", "Chinese Simplified")
        assert result["text"] == "你好世界"
        assert result["characters"] == 11

    @patch('httpx.post')
    def test_translate_unsupported_language(self, mock_post, deeplx_instance):
        result = deeplx_instance.translate("Hello", "Klingon")
        assert result["text"] == ""
        assert result["characters"] == 5

    @patch('httpx.post')
    def test_translate_rate_limit(self, mock_post, deeplx_instance):
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        result = deeplx_instance.translate("Hello", "Chinese Simplified")
        assert result["text"] == ""
        assert result["characters"] == 5

    @patch('httpx.post')
    def test_translate_validate_mode(self, mock_post, deeplx_instance):
        mock_response = Mock()
        mock_response.json.return_value = {"data": "你好"}
        mock_post.return_value = mock_response
        
        with patch('time.sleep') as mock_sleep:
            deeplx_instance.translate("Hello", "Chinese Simplified", validate=True)
            mock_sleep.assert_not_called()