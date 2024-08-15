import pytest
from unittest.mock import patch
from ..models.core import Translated_Content

def test_translated_content_hash_generation():
    content = Translated_Content(original_content="Hello", translated_language="zh")
    assert content.hash is not None
    assert len(content.hash) == 39  # CityHash128的长度

@pytest.mark.parametrize("text,language,expected", [
    ("Hello", "zh", {"text": "你好", "tokens": 2, "characters": 2}),
    ("Bonjour", "en", None)
])
def test_translated_content_is_translated(text, language, expected):
    with patch('v2.models.core.Translated_Content.objects.get') as mock_get:
        if expected:
            mock_get.return_value = Translated_Content(
                translated_content=expected["text"],
                tokens=expected["tokens"],
                characters=expected["characters"]
            )
        else:
            mock_get.side_effect = Translated_Content.DoesNotExist()
        
        result = Translated_Content.is_translated(text, language)
        assert result == expected