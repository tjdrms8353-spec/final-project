import json

import httpx
import pytest

from app.features.trends.translation import TranslationError, endpoint, translate

KEY = "secret-key:fx"


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_endpoint_by_key_type():
    assert endpoint("abc:fx") == "https://api-free.deepl.com/v2/translate"
    assert endpoint("abc") == "https://api.deepl.com/v2/translate"


def test_translates_in_order_and_skips_empty_texts():
    seen = {}
    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"translations": [{"text": "제목"}, {"text": "요약"}]})
    with client(handler) as c:
        assert translate(["Title", "", "Summary"], api_key=KEY, client=c) == ["제목", "", "요약"]
    assert seen["auth"] == f"DeepL-Auth-Key {KEY}"
    assert seen["body"] == {"text": ["Title", "Summary"], "source_lang": "EN", "target_lang": "KO"}


def test_all_empty_sends_nothing():
    with client(lambda request: pytest.fail("no request expected")) as c:
        assert translate(["", " "], api_key=KEY, client=c) == ["", " "]


@pytest.mark.parametrize("status,code,calls", [(400, "http_status", 1), (456, "quota_exceeded", 1),
                                               (429, "rate_limited", 3), (403, "invalid_api_key", 1),
                                               (500, "http_status", 3)])
def test_errors_are_sanitized(status, code, calls, monkeypatch):
    delays = []
    monkeypatch.setattr("app.features.trends.translation.time.sleep", delays.append)
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(status, text="private body")
    with client(handler) as c:
        with pytest.raises(TranslationError) as error:
            translate(["Title"], api_key=KEY, client=c)
    assert (error.value.code, error.value.status_code) == (code, status)
    assert "secret" not in str(error.value) and "private" not in str(error.value)
    assert len(seen) == calls
    assert delays == ([1, 2] if calls == 3 else [])


@pytest.mark.parametrize("status", [429, 503])
def test_transient_error_recovers_after_backoff(status, monkeypatch):
    delays = []
    monkeypatch.setattr("app.features.trends.translation.time.sleep", delays.append)
    seen = []
    def handler(request):
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(status)
        return httpx.Response(200, json={"translations": [{"text": "제목"}]})
    with client(handler) as c:
        assert translate(["Title"], api_key=KEY, client=c) == ["제목"]
    assert len(seen) == 2
    assert delays == [1]


def test_missing_key_and_size_limit():
    with pytest.raises(TranslationError, match="missing_api_key"):
        translate(["x"], api_key="")
    with pytest.raises(ValueError):
        translate(["x"] * 51, api_key=KEY)


def test_mismatched_response_is_rejected():
    with client(lambda request: httpx.Response(200, json={"translations": []})) as c:
        with pytest.raises(TranslationError, match="invalid_response"):
            translate(["Title"], api_key=KEY, client=c)
