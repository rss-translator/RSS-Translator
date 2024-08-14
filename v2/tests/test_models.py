import pytest
from sqlmodel import Session, SQLModel, create_engine
from v2.models.core import Engine, OFeed, TFeed, TranslatedContent, OpenAIInterface
from datetime import datetime
from uuid import uuid4

@pytest.fixture(scope="module")
def engine():
    return create_engine("sqlite:///:memory:")

@pytest.fixture(scope="module")
def session(engine):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_engine(session):
    engine = Engine(name="测试引擎", valid=True, is_ai=False)
    session.add(engine)
    session.commit()
    
    assert engine.id is not None
    assert engine.name == "测试引擎"
    assert engine.valid is True
    assert engine.is_ai is False

def test_ofeed(session):
    ofeed = OFeed(
        sid=str(uuid4()),
        name="测试订阅源",
        feed_url="http://example.com/feed",
        last_updated=datetime.now(),
        last_pull=datetime.now(),
        translation_display=1,
        etag="etag123",
        size=100,
        valid=True,
        update_frequency=60,
        max_posts=30,
        quality=True,
        fetch_article=True,
        summary_detail=0.5,
        additional_prompt="额外提示",
        category="测试分类"
    )
    session.add(ofeed)
    session.commit()
    
    assert ofeed.id is not None
    assert ofeed.name == "测试订阅源"
    assert ofeed.feed_url == "http://example.com/feed"

def test_tfeed(session):
    ofeed = OFeed(sid=str(uuid4()), feed_url="http://example2.com/feed")
    session.add(ofeed)
    session.commit()
    
    tfeed = TFeed(
        sid=str(uuid4()),
        language="zh-CN",
        status=True,
        translate_title=True,
        translate_content=True,
        summary=True,
        total_tokens=1000,
        total_characters=5000,
        modified=datetime.now(),
        size=200,
        o_feed=ofeed
    )
    session.add(tfeed)
    session.commit()
    
    assert tfeed.id is not None
    assert tfeed.language == "zh-CN"
    assert tfeed.o_feed_id == ofeed.id

def test_translated_content(session):
    content = TranslatedContent(
        hash="hash123",
        original_content="Hello",
        translated_language="zh-CN",
        translated_content="你好",
        tokens=2,
        characters=2
    )
    session.add(content)
    session.commit()
    
    assert content.hash == "hash123"
    assert content.original_content == "Hello"
    assert content.translated_content == "你好"

def test_openai_interface():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    # 创建会话
    with Session(engine) as local_session:
        openai = OpenAIInterface(
            name="OpenAI测试",
            api_key="test_key",
            base_url="https://api.openai.com/v1",
            model="gpt-3.5-turbo",
            translate_prompt="翻译提示",
            content_translate_prompt="内容翻译提示",
            temperature=0.5,
            top_p=0.5,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            max_tokens=1000,
            summary_prompt="总结提示"
        )
        local_session.add(openai)
        local_session.commit()
        
        assert openai.id is not None
        assert openai.name == "OpenAI测试"
        assert openai.api_key == "test_key"
        assert openai.is_ai is True

# 注意：这些测试用例可能需要根据实际情况进行调整和补充
