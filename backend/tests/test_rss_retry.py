import httpx
import pytest
from app.features.trends.collectors.retry import collect_with_retry, retry_delay
from app.features.trends.collectors.rss import RssCollectionError


@pytest.mark.parametrize("status,calls", [(403, 1), (429, 3), (503, 3)])
def test_bounded_requests(status, calls):
    seen, waits = [], []
    def handler(request):
        seen.append(request)
        return httpx.Response(status, headers={"Retry-After": "3"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RssCollectionError):
            collect_with_retry(client=client, sleep=waits.append)
    assert len(seen) == calls
    assert waits == ([3, 4] if calls == 3 else [])


def test_long_delay_never_retries_early():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429, headers={"Retry-After": "120"}))) as client:
        with pytest.raises(RssCollectionError) as error:
            collect_with_retry(client=client, sleep=lambda delay: pytest.fail("Should defer"))
    assert error.value.attempts == 1
    assert error.value.retry_after == 120


def test_timeout_then_success():
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("timeout")
        return httpx.Response(200, content=b'<rss><channel/></rss>')
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert collect_with_retry(client=client, sleep=lambda _: None).items == []
    assert len(calls) == 2


def test_delay_parsing():
    assert retry_delay("invalid") is None
    assert retry_delay("5") == 5
    assert retry_delay("Wed, 18 Nov 2020 00:00:00 GMT") == 0
