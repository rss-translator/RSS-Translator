import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.core import Translated_Content, Base

@pytest.fixture(scope="module")
def engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture(scope="module")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def dbsession(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_translated_content_creation(dbsession):
    # 测试创建新的翻译内容
    content = Translated_Content(
        original_content="Hello",
        translated_language="fr",
        translated_content="Bonjour",
        tokens=1,
        characters=5,
    )
    dbsession.add(content)
    dbsession.commit()

    # 验证创建的内容
    retrieved = (
        dbsession.query(Translated_Content).filter_by(original_content="Hello").first()
    )
    assert retrieved is not None
    assert retrieved.translated_content == "Bonjour"
    assert retrieved.translated_language == "fr"
    assert retrieved.tokens == 1
    assert retrieved.characters == 5


def test_is_translated(dbsession):
    # 测试is_translated方法
    content = Translated_Content(
        original_content="Good morning",
        translated_language="es",
        translated_content="Buenos días",
        tokens=2,
        characters=11,
    )
    dbsession.add(content)
    dbsession.commit()

    # 测试存在的翻译
    result = Translated_Content.is_translated("Good morning", "es", dbsession)
    assert result is not None
    assert result["text"] == "Buenos días"
    assert result["tokens"] == 2
    assert result["characters"] == 11

    # 测试不存在的翻译
    assert Translated_Content.is_translated("Goodbye", "fr", dbsession) is None


def test_hash_generation(dbsession):
    # 测试哈希生成
    content = Translated_Content(
        original_content="Test", translated_language="de", translated_content="Test"
    )
    dbsession.add(content)
    dbsession.commit()

    assert content.hash is not None
    assert len(content.hash) == 39
