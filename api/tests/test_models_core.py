import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models.core import Base, User, Engine, OpenAIInterface, FeedConfig, Feed, Cache, TranslationCache, SummaryCache, Setting
from api import settings

@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_user_creation(db_session):
    user = User(username="testuser", password_hash="hashed_password")
    db_session.add(user)
    db_session.commit()
    
    assert db_session.query(User).filter_by(username="testuser").first() is not None

def test_engine_creation(db_session):
    engine = Engine(name="TestEngine", valid=True, is_ai=False)
    db_session.add(engine)
    db_session.commit()
    
    assert db_session.query(Engine).filter_by(name="TestEngine").first() is not None

def test_openai_interface_creation(db_session):
    openai = OpenAIInterface(
        name="OpenAI",
        api_key="test_key",
        model="gpt-3.5-turbo",
        max_tokens=1000
    )
    db_session.add(openai)
    db_session.commit()
    
    assert db_session.query(OpenAIInterface).filter_by(name="OpenAI").first() is not None

# def test_category_creation(db_session):
#     category = Category(name="TestCategory")
#     db_session.add(category)
#     db_session.commit()
    
#     assert db_session.query(Category).filter_by(name="TestCategory").first() is not None

def test_feed_config_creation(db_session):
    config = FeedConfig(
        name="TestConfig",
        default=True,
        update_frequency=60,
        max_posts=10
    )
    db_session.add(config)
    db_session.commit()
    
    assert db_session.query(FeedConfig).filter_by(name="TestConfig").first() is not None

def test_feed_creation(db_session):
    config = db_session.query(FeedConfig).first()
    feed = Feed(
        name="TestFeed",
        feed_url="http://example.com/feed",
        feed_config=config
    )
    db_session.add(feed)
    db_session.commit()
    
    assert db_session.query(Feed).filter_by(name="TestFeed").first() is not None

def test_cache_creation(db_session):
    engine = db_session.query(Engine).first()
    cache = TranslationCache(
        original_content="Hello",
        target_language="es",
        target_content="Hola",
        engine=engine
    )
    db_session.add(cache)
    db_session.commit()
    
    assert db_session.query(TranslationCache).filter_by(original_content="Hello").first() is not None

def test_setting_creation(db_session):
    setting = Setting(name="TestSetting", value="TestValue")
    db_session.add(setting)
    db_session.commit()
    
    assert db_session.query(Setting).filter_by(name="TestSetting").first() is not None

def test_engine_min_max_size():
    engine = Engine(name="TestEngine")
    assert engine.min_size() == 0
    assert engine.max_size() == 0

def test_openai_interface_client():
    openai = OpenAIInterface(api_key="test_key", base_url="https://api.openai.com/v1")
    assert openai.client is not None

def test_cache_generate_hash():
    hash_value = Cache.generate_hash("test_text", "en")
    assert isinstance(hash_value, str)
    assert len(hash_value) > 0

def test_feed_config_get_translation_display():
    config = FeedConfig(translation_display=1)
    assert config.get_translation_display() == "Translation | Original"
