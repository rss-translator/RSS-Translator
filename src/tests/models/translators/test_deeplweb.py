import pytest
from unittest.mock import patch, MagicMock
from src.models.translators.deeplweb import DeepLWeb

class TestDeepLWeb:

    @pytest.fixture
    def deepl_instance(self):
        return DeepLWeb()

    def test_validate_success(self, deepl_instance):
        with patch.object(deepl_instance, 'translate') as mock_translate:
            mock_translate.return_value = {"text": "你好世界"}
            assert deepl_instance.validate() is True
            mock_translate.assert_called_once_with("Hello World", "Chinese Simplified", validate=True)

    def test_validate_failure(self, deepl_instance):
        with patch.object(deepl_instance, 'translate') as mock_translate:
            mock_translate.return_value = {"text": ""}
            assert deepl_instance.validate() is False
            mock_translate.assert_called_once_with("Hello World", "Chinese Simplified", validate=True)

    def test_validate_exception(self, deepl_instance):
        with patch.object(deepl_instance, 'translate') as mock_translate:
            mock_translate.side_effect = Exception("Test exception")
            assert deepl_instance.validate() is False
            mock_translate.assert_called_once_with("Hello World", "Chinese Simplified", validate=True)

    def test_translate_success(self, deepl_instance):
        with patch('src.models.translators.deeplweb.PyDeepLX') as mock_pydeeplx:
            mock_pydeeplx.translate.return_value = "你好世界"
            result = deepl_instance.translate("Hello World", "Chinese Simplified")
            assert result == {"text": "你好世界", "characters": 11}
            mock_pydeeplx.translate.assert_called_once_with(
                text="Hello World", targetLang="ZH", sourceLang="auto", proxies=None
            )

    def test_translate_unsupported_language(self, deepl_instance):
        result = deepl_instance.translate("Hello World", "Unsupported Language")
        assert result == {"text": "", "characters": 11}

    def test_translate_exception(self, deepl_instance):
        with patch('src.models.translators.deeplweb.PyDeepLX') as mock_pydeeplx:
            mock_pydeeplx.translate.side_effect = Exception("Test exception")
            result = deepl_instance.translate("Hello World", "Chinese Simplified")
            assert result == {"text": "", "characters": 11}

    def test_language_code_map(self, deepl_instance):
        assert deepl_instance.language_code_map["English"] == "EN"
        assert deepl_instance.language_code_map["Chinese Simplified"] == "ZH"
        assert deepl_instance.language_code_map["Russian"] == "RU"

    @patch('src.models.translators.deeplweb.sleep')
    def test_translate_sleep(self, mock_sleep, deepl_instance):
        deepl_instance.interval = 5
        with patch('src.models.translators.deeplweb.PyDeepLX'):
            deepl_instance.translate("Hello World", "Chinese Simplified")
            mock_sleep.assert_called_once_with(5)

    def test_translate_no_sleep_on_validate(self, deepl_instance):
        with patch('src.models.translators.deeplweb.sleep') as mock_sleep:
            with patch('src.models.translators.deeplweb.PyDeepLX'):
                deepl_instance.translate("Hello World", "Chinese Simplified", validate=True)
                mock_sleep.assert_not_called()