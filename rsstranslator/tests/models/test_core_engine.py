import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from rsstranslator.backend.models.core import Base, Engine

@pytest.fixture(scope="module")
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_engine_min_size():
    engine = Engine()
    assert engine.min_size() == 0

def test_engine_max_size():
    engine = Engine()
    assert engine.max_size() == 0

def test_engine_translate_not_implemented():
    with pytest.raises(NotImplementedError):
        Engine().translate("test", "zh")

def test_engine_validate_not_implemented():
    with pytest.raises(NotImplementedError):
        Engine().validate()

def test_engine_database_operations(db_session):
    # 创建新引擎
    new_engine = Engine(name="Test", is_available=True, is_ai=False)
    db_session.add(new_engine)
    db_session.commit()

    # 查询并验证
    queried_engine = db_session.query(Engine).filter_by(name="Test").first()
    assert queried_engine is not None
    assert queried_engine.name == "Test"
    assert queried_engine.is_available is True
    assert queried_engine.is_ai is False

    # 更新并验证
    queried_engine.is_available = False
    db_session.commit()
    db_session.refresh(queried_engine)
    assert queried_engine.is_available is False

    # 删除并验证
    db_session.delete(queried_engine)
    db_session.commit()
    deleted_engine = db_session.query(Engine).filter_by(name="Test").first()
    assert deleted_engine is None