import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rsstranslator.backend.models.core import Cache, Base, Engine


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def sample_engine(db_session):
    engine = Engine(name="TestEngine", is_available=True, is_ai=False)
    db_session.add(engine)
    db_session.commit()
    return engine


def test_cache_init(db_session, sample_engine):
    cache = Cache(
        original_content="Hello, world!",
        target_language="es",
        target_content="¡Hola, mundo!",
        tokens=5,
        characters=13,
        engine=sample_engine,
    )
    db_session.add(cache)
    db_session.commit()
    assert cache.hash == Cache.generate_hash("Hello, world!", "es")
    assert cache.original_content == "Hello, world!"
    assert cache.target_language == "es"
    assert cache.target_content == "¡Hola, mundo!"
    assert cache.tokens == 5
    assert cache.characters == 13
    assert cache.engine == sample_engine


def test_generate_hash():
    hash1 = Cache.generate_hash("Hello, world!", "es")
    hash2 = Cache.generate_hash("Hello, world!", "fr")
    hash3 = Cache.generate_hash("Bonjour, monde!", "fr")

    assert hash1 != hash2
    assert hash2 != hash3
    assert hash1 != hash3


def test_is_translated_existing(db_session, sample_engine):
    original_text = "Hello, world!"
    target_language = "es"

    result = Cache.is_translated(original_text, target_language, db_session)
    assert result is not None
    assert result["text"] == "¡Hola, mundo!"
    assert result["tokens"] == 5
    assert result["characters"] == 13


def test_is_translated_non_existing(db_session):
    result = Cache.is_translated("This text is not cached", "fr", db_session)
    assert result is None


def test_cache_polymorphic_identity(db_session, sample_engine):
    translation_cache = Cache(
        original_content="Hello",
        target_language="es",
        target_content="Hola",
        engine=sample_engine,
        type="Translation Cache",
    )
    summary_cache = Cache(
        original_content="Long text...",
        target_language="en",
        target_content="Summary...",
        engine=sample_engine,
        type="Summary Cache",
    )

    db_session.add(translation_cache)
    db_session.add(summary_cache)
    db_session.commit()

    assert translation_cache.type == "Translation Cache"
    assert summary_cache.type == "Summary Cache"
