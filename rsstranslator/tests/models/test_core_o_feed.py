import pytest
from rsstranslator.backend.models.core import O_Feed

@pytest.fixture
def o_feed():
    return O_Feed(feed_url="https://example.com/feed")

def test_o_feed_sid_generation(o_feed):
    assert o_feed.sid is not None
    assert len(o_feed.sid) == 32  # UUID5的长度

def test_o_feed_get_translation_display():
    feed = O_Feed()
    feed.translation_display = 0
    assert feed.get_translation_display() == "Only Translation"
    
    feed.translation_display = 1
    assert feed.get_translation_display() == "Translation | Original"
    
    feed.translation_display = 2
    assert feed.get_translation_display() == "Original | Translation"

def test_o_feed_database_operations():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from rsstranslator.backend.models.core import Base, O_Feed, OpenAIInterface

    # 创建内存数据库
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    
    # 创建会话
    session = Session()

    # 创建OpenAIInterface实例
    translator = OpenAIInterface(name="测试翻译器", api_key="test_key", model="gpt-3.5-turbo")
    summary_engine = OpenAIInterface(name="测试摘要引擎", api_key="test_key", model="gpt-3.5-turbo")
    session.add(translator)
    session.add(summary_engine)
    session.commit()

    # 测试写入操作
    new_feed = O_Feed(
        name="测试订阅源",
        feed_url="https://example.com/test_feed",
        translation_display=1,
        update_frequency=60,
        max_posts=30,
        quality=True,
        fetch_article=True,
        translator=translator,
        summary_engine=summary_engine
    )
    session.add(new_feed)
    session.commit()

    # 测试读取操作
    queried_feed = session.query(O_Feed).filter_by(name="测试订阅源").first()
    assert queried_feed is not None
    assert queried_feed.name == "测试订阅源"
    assert queried_feed.feed_url == "https://example.com/test_feed"
    assert queried_feed.translation_display == 1
    assert queried_feed.update_frequency == 60
    assert queried_feed.max_posts == 30
    assert queried_feed.quality is True
    assert queried_feed.fetch_article is True
    assert queried_feed.translator.name == "测试翻译器"
    assert queried_feed.summary_engine.name == "测试摘要引擎"

    # 测试更新操作
    queried_feed.max_posts = 50
    session.commit()
    updated_feed = session.query(O_Feed).filter_by(name="测试订阅源").first()
    assert updated_feed.max_posts == 50

    # 测试删除操作
    session.delete(queried_feed)
    session.commit()
    deleted_feed = session.query(O_Feed).filter_by(name="测试订阅源").first()
    assert deleted_feed is None

    # 关闭会话
    session.close()
