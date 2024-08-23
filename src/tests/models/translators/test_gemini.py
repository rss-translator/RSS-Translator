import pytest
from unittest.mock import patch, MagicMock
from src.models.translators.gemini import Gemini


class TestGemini:
    @pytest.fixture
    def gemini_instance(self):
        return Gemini(
            api_key="test_api_key",
            model="google-gemini",
            title_translate_prompt="Translate to {target_language}",
            content_translate_prompt="Translate content to {target_language}",
            temperature=0.2,
            top_p=0.2,
            frequency_penalty=0,
            presence_penalty=0,
            max_tokens=2000,
            summary_prompt="Summarize in {target_language}",
            interval=5,
        )

    @patch("src.models.translators.gemini.genai.GenerativeModel")
    def test_validate_success(self, mock_generative_model, gemini_instance):
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock(finish_reason=1)]
        mock_generative_model.return_value.generate_content.return_value = mock_response

        result = gemini_instance.validate()

        assert result is True
        mock_generative_model.return_value.generate_content.assert_called_once_with(
            "hi"
        )

    @patch("src.models.translators.gemini.genai.GenerativeModel")
    def test_validate_failure(self, mock_generative_model, gemini_instance):
        mock_generative_model.return_value.generate_content.side_effect = Exception(
            "API错误"
        )

        result = gemini_instance.validate()

        assert result is False

    @patch("src.models.translators.gemini.genai.GenerativeModel")
    @patch("src.models.translators.gemini.sleep")
    def test_translate_success(
        self, mock_sleep, mock_generative_model, gemini_instance
    ):
        mock_response = MagicMock()
        mock_response.text = "翻译后的文本"
        mock_response.candidates = [MagicMock(finish_reason=1)]
        mock_generative_model.return_value.generate_content.return_value = mock_response
        mock_generative_model.return_value.count_tokens.return_value.total_tokens = 10

        result = gemini_instance.translate("Hello", "zh-CN")

        assert result == {"text": "翻译后的文本", "tokens": 10}
        mock_sleep.assert_called_once_with(5)

    @patch("src.models.translators.gemini.genai.GenerativeModel")
    @patch("src.models.translators.gemini.sleep")
    def test_translate_failure(
        self, mock_sleep, mock_generative_model, gemini_instance
    ):
        mock_generative_model.return_value.generate_content.side_effect = Exception(
            "API错误"
        )

        result = gemini_instance.translate("Hello", "zh-CN")

        assert result == {"text": "", "tokens": 0}
        mock_sleep.assert_called_once_with(5)

    def test_summarize(self, gemini_instance):
        with patch.object(gemini_instance, "translate") as mock_translate:
            mock_translate.return_value = {"text": "摘要", "tokens": 5}

            result = gemini_instance.summarize("长文本", "zh-CN")

            assert result == {"text": "摘要", "tokens": 5}
            mock_translate.assert_called_once_with(
                "长文本", "zh-CN", system_prompt=gemini_instance.summary_prompt
            )
