import json

import httpx
import pytest

from pipelines.jobs.collect_gdelt import main, run_job


def article(**overrides):
    return {
        "url": "https://example.com/1", "title": "Sample",
        "domain": "example.com", "seendate": "20260101T010000Z",
        **overrides,
    }


def test_default_dry_run_never_creates_a_client(monkeypatch):
    def forbid_client(*args, **kwargs):
        pytest.fail("Dry run must not create an HTTP client")

    monkeypatch.setattr(httpx, "Client", forbid_client)
    result = run_job("sample")
    assert result.status == "dry_run"
    assert result.batch is None
    assert result.summary()["input_count"] is None


@pytest.mark.parametrize("options", [
    {"query": " "}, {"timespan": "8d"}, {"max_records": 251},
    {"timeout": 0}, {"execute": "false"},
])
def test_invalid_options_fail_even_in_dry_run(options):
    with pytest.raises(ValueError):
        run_job(**{"query": "sample", **options})


def test_collection_preprocessing_and_summary_are_connected():
    def handler(request):
        assert request.url.params["query"] == "sample"
        return httpx.Response(200, json={"articles": [
            article(), article(url="https://example.com/1#duplicate"),
            article(title=" "),
            article(url="https://example.com/2", seendate="20260101T020000Z"),
        ]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = run_job("sample", execute=True, client=client)
        assert not client.is_closed
    assert result.summary() == {
        "status": "partial", "input_count": 4, "accepted_count": 2,
        "rejected_count": 1, "duplicate_count": 1,
        "error_code": None, "http_status": None,
    }
    assert str(result.batch.items[0].url) == "https://example.com/2"


@pytest.mark.parametrize("articles,status,code", [
    ([], "success", None),
    ([article()], "success", None),
    ([article(), article()], "success", None),
    ([article(title="")], "failed", "no_valid_articles"),
])
def test_empty_success_duplicates_and_all_invalid_are_distinguished(articles, status, code):
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"articles": articles}),
    )) as client:
        result = run_job("sample", execute=True, client=client)
    assert result.status == status
    assert result.error_code == code
    assert result.batch.input_count == len(articles)


def test_upstream_failure_has_no_fake_zero_counts_and_no_retries():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, text="private-body")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = run_job("private-query", execute=True, client=client)
    assert len(calls) == 1
    assert result.status == "failed"
    assert result.http_status == 429
    assert result.summary()["accepted_count"] is None
    assert "private" not in json.dumps(result.summary())


def test_cli_default_is_validation_only(capsys):
    assert main(["--query", "sample"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "dry_run"


def test_cli_invalid_options_return_two_without_echoing_values(capsys):
    assert main(["--query", "private-query", "--timespan", "bad-private-value"]) == 2
    output = capsys.readouterr().out
    assert json.loads(output)["error_code"] == "invalid_options"
    assert "private" not in output


@pytest.mark.parametrize("status,payload,exit_code", [
    (200, {"articles": [article()]}, 0),
    (200, {"articles": [article(), article(title="")]}, 1),
    (200, {"articles": [article(title="")]}, 1),
    (500, {}, 1),
])
def test_cli_execution_exit_codes_with_mock_transport(status, payload, exit_code, capsys):
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json=payload),
    )) as client:
        assert main(["--query", "sample", "--execute"], client=client) == exit_code
    assert "status" in json.loads(capsys.readouterr().out)
