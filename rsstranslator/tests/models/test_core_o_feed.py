import pytest
from rsstranslator.backend.models.core import O_Feed

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from rsstranslator.backend.models.core import Base, O_Feed, OpenAIInterface, Category

@pytest.fixture(scope="module")
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_o_feed_get_translation_display():
    feed = O_Feed()
    feed.translation_display = 0
    assert feed.get_translation_display() == "Only Translation"
    
    feed.translation_display = 1
    assert feed.get_translation_display() == "Translation | Original"
    
    feed.translation_display = 2
    assert feed.get_translation_display() == "Original | Translation"

def test_o_feed_database_operations(db_session):
    # 测试写入操作
    new_feed = O_Feed(
        name="Example Feed",
        feed_url="https://example.com/test_feed",
        translation_display=1,
        update_frequency=60,
        max_posts=30,
        quality=True,
        fetch_article=True
    )
    db_session.add(new_feed)
    db_session.commit()

    # 测试读取操作
    queried_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert queried_feed is not None
    assert queried_feed.name == "Example Feed"
    assert queried_feed.feed_url == "https://example.com/test_feed"
    assert queried_feed.translation_display == 1
    assert queried_feed.update_frequency == 60
    assert queried_feed.max_posts == 30
    assert queried_feed.quality is True
    assert queried_feed.fetch_article is True

    # 测试更新操作
    queried_feed.max_posts = 50
    db_session.commit()
    updated_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert updated_feed.max_posts == 50

    # 测试删除操作
    db_session.delete(queried_feed)
    db_session.commit()
    deleted_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert deleted_feed is None

    # 关闭会话
    db_session.close()

def test_o_feed_database_operations_with_engine(db_session):
    # 创建OpenAIInterface实例
    translator = OpenAIInterface(name="Test Translator", api_key="test_key", model="gpt-3.5-turbo")
    summary_engine = OpenAIInterface(name="Test Summary Engine", api_key="test_key", model="gpt-3.5-turbo")
    db_session.add(translator)
    db_session.add(summary_engine)
    db_session.commit()

    # 测试写入操作
    new_feed = O_Feed(
        name="Example Feed",
        feed_url="https://example.com/test_feed",
        translation_display=1,
        update_frequency=60,
        max_posts=30,
        quality=True,
        fetch_article=True,
        translator=translator,
        summary_engine=summary_engine
    )
    db_session.add(new_feed)
    db_session.commit()

    # 测试读取操作
    queried_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert queried_feed is not None
    assert queried_feed.name == "Example Feed"
    assert queried_feed.feed_url == "https://example.com/test_feed"
    assert queried_feed.translation_display == 1
    assert queried_feed.update_frequency == 60
    assert queried_feed.max_posts == 30
    assert queried_feed.quality is True
    assert queried_feed.fetch_article is True
    assert queried_feed.translator.name == "Test Translator"
    assert queried_feed.summary_engine.name == "Test Summary Engine"
    assert translator.translated_feeds == [queried_feed]
    assert summary_engine.summarized_feeds == [queried_feed]

    # 测试更新操作
    queried_feed.max_posts = 50
    db_session.commit()
    updated_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert updated_feed.max_posts == 50

    # 测试删除操作
    db_session.delete(queried_feed)
    db_session.commit()
    deleted_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert deleted_feed is None

    # 关闭会话
    db_session.close()

def test_o_feed_database_operations_with_category(db_session):
    # 测试写入操作
    new_feed = O_Feed(
        name="Example Feed",
        feed_url="https://example.com/test_feed",
        translation_display=1,
        update_frequency=60,
        max_posts=30,
        quality=True,
        fetch_article=True
    )
    new_category = Category(name="Test Category")
    new_feed.category = new_category
    db_session.add(new_feed)
    db_session.add(new_category)
    db_session.commit()

    # 测试读取操作
    queried_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert queried_feed is not None
    assert queried_feed.name == "Example Feed"
    assert queried_feed.feed_url == "https://example.com/test_feed"
    assert queried_feed.translation_display == 1
    assert queried_feed.update_frequency == 60
    assert queried_feed.max_posts == 30
    assert queried_feed.quality is True
    assert queried_feed.fetch_article is True
    assert queried_feed.category.name == "Test Category"

    # 测试更新操作
    queried_feed.max_posts = 50
    db_session.commit()
    updated_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert updated_feed.max_posts == 50

    # 测试删除操作
    db_session.delete(queried_feed)
    db_session.commit()
    deleted_feed = db_session.query(O_Feed).filter_by(name="Example Feed").first()
    assert deleted_feed is None

    # 关闭会话
    db_session.close()

