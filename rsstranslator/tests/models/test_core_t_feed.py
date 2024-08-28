import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from datetime import datetime,UTC
from rsstranslator.backend.models.core import Base, T_Feed, O_Feed

@pytest.fixture(scope="module")
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        

@pytest.fixture(scope="module")
def sample_o_feed(db_session):
    o_feed = O_Feed(feed_url="http://example.com/feed")
    db_session.add(o_feed)
    db_session.commit()
    return o_feed

def test_create_t_feed(db_session, sample_o_feed):
    t_feed = T_Feed(
        language="zh-CN",
        o_feed_id=sample_o_feed.id,
        status=True,
        translate_title=True,
        translate_content=True,
        summary=False,
        total_tokens=1000,
        total_characters=5000,
        modified=datetime.now(UTC),
        size=10240
    )
    db_session.add(t_feed)
    db_session.commit()

    assert t_feed.id is not None
    assert t_feed.language == "zh-CN"
    assert t_feed.o_feed_id == sample_o_feed.id
    assert t_feed.status is True
    assert t_feed.translate_title is True
    assert t_feed.translate_content is True
    assert t_feed.summary is False
    assert t_feed.total_tokens == 1000
    assert t_feed.total_characters == 5000
    assert t_feed.size == 10240

def test_t_feed_o_feed_relationship(db_session, sample_o_feed):
    t_feed = T_Feed(
        language="en-US",
        o_feed_id=sample_o_feed.id,
        status=True
    )
    db_session.add(t_feed)
    db_session.commit()

    assert t_feed.o_feed == sample_o_feed
    assert t_feed in sample_o_feed.t_feeds

def test_unique_constraint(db_session, sample_o_feed):
    t_feed1 = T_Feed(language="fr-FR", o_feed_id=sample_o_feed.id)
    db_session.add(t_feed1)
    db_session.commit()

    t_feed2 = T_Feed(language="fr-FR", o_feed_id=sample_o_feed.id)
    new_session = Session(db_session.bind)
    
    with pytest.raises(Exception):
        new_session.add(t_feed2)
        new_session.commit()
    
    new_session.close()

def test_default_values(db_session, sample_o_feed):
    t_feed = T_Feed(language="es-ES", o_feed_id=sample_o_feed.id)
    db_session.add(t_feed)
    db_session.commit()

    assert t_feed.translate_title is False
    assert t_feed.translate_content is False
    assert t_feed.summary is False
    assert t_feed.total_tokens == 0
    assert t_feed.total_characters == 0
    assert t_feed.size == 0

def test_update_t_feed(db_session, sample_o_feed):
    t_feed = T_Feed(language="it-IT", o_feed_id=sample_o_feed.id)
    db_session.add(t_feed)
    db_session.commit()

    t_feed.status = True
    t_feed.translate_title = True
    t_feed.total_tokens = 500
    db_session.commit()

    updated_t_feed = db_session.query(T_Feed).filter_by(id=t_feed.id).first()
    assert updated_t_feed.status is True
    assert updated_t_feed.translate_title is True
    assert updated_t_feed.total_tokens == 500
