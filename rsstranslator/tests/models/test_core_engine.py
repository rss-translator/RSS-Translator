import pytest
from rsstranslator.backend.models.core import Engine

def test_engine_min_size():
    engine = Engine()
    engine.max_characters = 1000
    assert engine.min_size() == 700

def test_engine_max_size():
    engine = Engine()
    engine.max_tokens = 1000
    assert engine.max_size() == 900

def test_engine_translate_not_implemented():
    engine = Engine()
    with pytest.raises(NotImplementedError):
        engine.translate("test", "zh")

def test_engine_validate_not_implemented():
    engine = Engine()
    with pytest.raises(NotImplementedError):
        engine.validate()

def test_engine_database_operations():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from rsstranslator.backend.models.core import Base, Engine

    # 创建内存数据库
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    
    # 创建会话
    session = Session()

    # 测试写入操作
    new_engine = Engine(name="测试引擎", valid=True, is_ai=False)
    session.add(new_engine)
    session.commit()

    # 测试读取操作
    queried_engine = session.query(Engine).filter_by(name="测试引擎").first()
    assert queried_engine is not None
    assert queried_engine.name == "测试引擎"
    assert queried_engine.valid is True
    assert queried_engine.is_ai is False

    # 测试更新操作
    queried_engine.valid = False
    session.commit()
    updated_engine = session.query(Engine).filter_by(name="测试引擎").first()
    assert updated_engine.valid is False

    # 测试删除操作
    session.delete(queried_engine)
    session.commit()
    deleted_engine = session.query(Engine).filter_by(name="测试引擎").first()
    assert deleted_engine is None

    # 关闭会话
    session.close()
