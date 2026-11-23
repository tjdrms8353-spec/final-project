import pytest
from pipelines.jobs.collection_lock import collection_lock, CollectionBusy
import pipelines.jobs.rss_history as history


def test_same_feed_blocked_different_feed_allowed_and_released():
    with collection_lock('test-feed-one'):
        with pytest.raises(CollectionBusy):
            with collection_lock('test-feed-one'):
                pass
        with collection_lock('test-feed-two'):
            pass
    with collection_lock('test-feed-one'):
        pass


def test_exception_releases_lock():
    with pytest.raises(ValueError):
        with collection_lock('test-exception'):
            raise ValueError()
    with collection_lock('test-exception'):
        pass


def test_busy_job_never_connects_or_collects():
    with collection_lock('test-busy'):
        result = history.execute_stored(None, feed='test-busy', limit=5, timeout=2)
    assert result['error_code'] == 'collection_busy'
    assert result['storage'] == 'not_started'
