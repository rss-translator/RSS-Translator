import pytest
from src.models.core import T_Feed, O_Feed

@pytest.fixture
def t_feed():
    o_feed = O_Feed(sid="test_sid", feed_url="https://example.com/feed")
    return T_Feed(o_feed=o_feed, language="zh")

def test_t_feed_sid_generation(t_feed):
    assert t_feed.sid == "test_sid_zh"