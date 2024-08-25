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