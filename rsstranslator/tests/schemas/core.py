from pydantic_core import Url
import pytest
from pydantic import ValidationError
from rsstranslator.backend.schemas.core import (
    EngineBase, EngineCreate, Engine,
    OpenAIInterfaceBase, OpenAIInterfaceCreate, OpenAIInterface,
    OFeedBase, OFeedCreate, OFeed,
    TFeedBase, TFeedCreate, TFeed,
    TranslatedContentBase, TranslatedContentCreate, TranslatedContent
)

def test_engine_base():
    engine = EngineBase(name="测试引擎", type="测试类型")
    assert engine.name == "测试引擎"
    assert engine.type == "测试类型"
    assert engine.valid is None
    assert engine.is_ai is False

def test_engine_create():
    engine = EngineCreate(name="测试引擎", type="测试类型")
    assert engine.name == "测试引擎"
    assert engine.type == "测试类型"

def test_engine():
    engine = Engine(id=1, name="测试引擎", type="测试类型")
    assert engine.id == 1
    assert engine.name == "测试引擎"
    assert engine.type == "测试类型"

def test_openai_interface_base():
    openai = OpenAIInterfaceBase(
        name="OpenAI测试",
        type="OpenAI",
        api_key="sk-test",
        title_translate_prompt="翻译标题",
        content_translate_prompt="翻译内容",
        summary_prompt="总结内容"
    )
    assert openai.name == "OpenAI测试"
    assert openai.api_key == "sk-test"
    assert openai.is_ai is True

def test_ofeed_base():
    ofeed = OFeedBase(feed_url="http://example.com/feed")
    assert ofeed.feed_url == Url("http://example.com/feed")
    assert ofeed.translation_display == 0
    assert ofeed.max_posts == 20

def test_tfeed_base():
    tfeed = TFeedBase(language="zh-CN")
    assert tfeed.language == "zh-CN"
    assert tfeed.translate_title is False
    assert tfeed.translate_content is False

def test_translated_content_base():
    content = TranslatedContentBase(
        original_content="Hello",
        translated_language="zh-CN",
        translated_content="你好"
    )
    assert content.original_content == "Hello"
    assert content.translated_language == "zh-CN"
    assert content.translated_content == "你好"

def test_invalid_url():
    with pytest.raises(ValidationError):
        OFeedBase(feed_url="不是有效的URL")