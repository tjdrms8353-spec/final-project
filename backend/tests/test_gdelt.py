import httpx
import pytest

from app.features.trends.collectors.gdelt import (
    ENDPOINT, GdeltCollectionError, collect_news, parse_gdelt_response,
)


def article(**overrides):
    return {
        "url": "https://example.com/news/1", "title": " 샘플\n 뉴스 ",
        "domain": "example.com", "seendate": "20260101T010000Z",
        "language": "Korean", "sourcecountry": "South Korea",
        **overrides,
    }


def test_request_parameters_and_mapping_without_network():
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url).split("?")[0] == ENDPOINT
        assert dict(request.url.params) == {
            "query": '"climate change"', "mode": "ArtList", "format": "json",
            "timespan": "1h", "maxrecords": "5", "sort": "DateDesc",
        }
        assert request.extensions["timeout"]["read"] == 3
        return httpx.Response(200, json={"articles": [article()]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        batch = collect_news(' "climate change" ', max_records=5, timeout=3, client=client)
        assert not client.is_closed
    assert len(calls) == 1
    assert batch.input_count == len(batch.items) == 1
    item = batch.items[0]
    assert item.title == "샘플 뉴스"
    assert item.published_at is None
    assert item.observed_at.isoformat() == "2026-01-01T01:00:00+00:00"
    assert item.id.startswith("gdelt-")


def test_mixed_results_are_validated_deduplicated_and_sorted():
    batch = parse_gdelt_response({"articles": [
        article(), article(url="https://EXAMPLE.com:443/news/1#top"),
        article(url="https://example.com/news/2", seendate="20260101T020000Z"),
        article(title=" "), article(seendate="20260230T010000Z"), None,
    ]})
    assert batch.input_count == 6
    assert len(batch.items) == 2
    assert batch.duplicate_count == 1
    assert [entry.index for entry in batch.rejected] == [3, 4, 5]
    assert str(batch.items[0].url).endswith("/2")


def test_id_is_stable_for_same_canonical_url():
    first = parse_gdelt_response({"articles": [article()]})
    second = parse_gdelt_response({"articles": [
        article(url="https://EXAMPLE.com:443/news/1#part", title="Changed title"),
    ]})
    assert first.items[0].id == second.items[0].id


def test_empty_results_are_valid():
    batch = parse_gdelt_response({"articles": []})
    assert batch.input_count == 0
    assert batch.items == batch.rejected == []


@pytest.mark.parametrize("payload", [None, [], {}, {"articles": None}, {"articles": {}}])
def test_invalid_envelope_is_not_silently_treated_as_empty(payload):
    with pytest.raises(GdeltCollectionError) as error:
        parse_gdelt_response(payload)
    assert error.value.code == "invalid_payload"


@pytest.mark.parametrize("status", [302, 429, 500])
def test_http_errors_do_not_retry_or_expose_body(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="private-body")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GdeltCollectionError) as error:
            collect_news("private-query", client=client)
    assert len(calls) == 1
    assert error.value.code == "http_status"
    assert error.value.status_code == status
    assert "private" not in str(error.value)


@pytest.mark.parametrize("exception,code", [
    (httpx.ReadTimeout, "timeout"), (httpx.ConnectError, "network"),
])
def test_transport_errors(exception, code):
    def handler(request):
        raise exception("private-error", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GdeltCollectionError) as error:
            collect_news("sample", client=client)
    assert error.value.code == code
    assert "private" not in str(error.value)


def test_non_json_response_is_an_error():
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, text="API error message"),
    )) as client:
        with pytest.raises(GdeltCollectionError) as error:
            collect_news("sample", client=client)
    assert error.value.code == "invalid_json"


@pytest.mark.parametrize("kwargs", [
    {"query": " "}, {"query": None},
    {"max_records": 0}, {"max_records": 251}, {"max_records": True},
    {"timespan": "0h"}, {"timespan": "14min"}, {"timespan": "8d"},
    {"timespan": "1month"}, {"timeout": 0}, {"timeout": float("inf")},
])
def test_invalid_options_fail_before_any_request(kwargs):
    def handler(request):
        pytest.fail("Invalid options must not issue requests")

    options = {"query": "sample", **kwargs}
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            collect_news(**options, client=client)
