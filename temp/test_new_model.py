import pytest
from sqlmodel import SQLModel, Session, create_engine
from .new_model import Feed, Translation, GoogleTranslation, BaiduTranslation, TranslationServiceType

@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    return engine

@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session

def test_create_feed(session):
    feed = Feed(url="http://example.com/rss")
    session.add(feed)
    session.commit()

    db_feed = session.query(Feed).first()
    assert db_feed.url == "http://example.com/rss"
    #assert db_feed.translation_service == TranslationServiceType.GOOGLE

def test_create_google_translation(session):
    feed = Feed(url="http://example.com/rss")
    translation = GoogleTranslation(
        api_key="your_api_key",
        source_lang="en",
        target_lang="zh",
        #feed=feed
    )
    
    session.add(translation)
    session.add(feed)
    session.commit()

    db_translation = session.query(GoogleTranslation).first()
    assert db_translation.api_key == "your_api_key"
    assert db_translation.source_lang == "en"
    assert db_translation.target_lang == "zh"
    assert feed.url == "http://example.com/rss"

def test_create_baidu_translation(session):
    feed = Feed(url="http://example.com/rss")
    translation = BaiduTranslation(
        app_id="your_app_id",
        app_key="your_app_key",
        from_lang="en",
        to_lang="zh",
        feed=feed
    )
    session.add(translation)
    session.commit()

    db_translation = session.query(BaiduTranslation).first()
    assert db_translation.app_id == "your_app_id"
    assert db_translation.app_key == "your_app_key"
    assert db_translation.from_lang == "en"
    assert db_translation.to_lang == "zh"
    assert db_translation.feed.url == "http://example.com/rss"

def test_feed_translation_relationship(session):
    feed = Feed(url="http://example.com/rss")
    translation = GoogleTranslation(
        api_key="your_api_key",
        source_lang="en",
        target_lang="zh",
        feed=feed
    )
    session.add(translation)
    session.commit()

    db_feed = session.query(Feed).first()
    assert db_feed.translation.type == TranslationServiceType.GOOGLE
    assert isinstance(db_feed.translation, GoogleTranslation)

def test_one_feed_one_translation(session):
    feed = Feed(url="http://example.com/rss")
    translation1 = GoogleTranslation(
        api_key="your_api_key",
        source_lang="en",
        target_lang="zh",
        feed=feed
    )
    translation2 = BaiduTranslation(
        app_id="your_app_id",
        app_key="your_app_key",
        from_lang="en",
        to_lang="zh",
        feed=feed
    )
    session.add(translation1)
    session.add(translation2)
    
    with pytest.raises(Exception):
        session.commit()