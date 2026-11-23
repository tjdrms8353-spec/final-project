from copy import deepcopy

from app.features.trends.preprocessing.news import prepare_news


def article(**overrides):
    return {
        "id": "news-1",
        "title": "  샘플\n 뉴스 ",
        "url": "https://example.com/1",
        "source": " 샘플 ",
        "published_at": "2026-01-01T09:00:00+09:00",
        **overrides,
    }


def test_empty_batch():
    batch = prepare_news([])
    assert batch.items == batch.rejected == []
    assert batch.input_count == batch.duplicate_count == 0


def test_mixed_batch_tracks_every_input_and_keeps_valid_news():
    batch = prepare_news([
        article(), article(title=" "), None,
        article(id="news-2", url="https://example.com/2"),
        article(),
    ])
    assert batch.input_count == 5
    assert len(batch.items) == 2
    assert len(batch.rejected) == 2
    assert batch.duplicate_count == 1
    assert batch.input_count == (
        len(batch.items) + len(batch.rejected) + batch.duplicate_count
    )
    assert [entry.index for entry in batch.rejected] == [1, 2]
    assert batch.rejected[0].errors[0]["field"] == "title"


def test_duplicate_id_or_normalized_url_keeps_first_valid_record():
    batch = prepare_news([
        article(url="https://EXAMPLE.com:443/1#top"),
        article(id="news-2", url="https://example.com/1#bottom"),
        article(url="https://example.com/different"),
    ])
    assert len(batch.items) == 1
    assert batch.duplicate_count == 2
    assert batch.items[0].id == "news-1"


def test_different_query_parameters_are_not_merged():
    batch = prepare_news([
        article(url="https://example.com/article?id=1"),
        article(id="news-2", url="https://example.com/article?id=2"),
    ])
    assert len(batch.items) == 2
    assert batch.duplicate_count == 0


def test_invalid_record_does_not_reserve_id_or_url():
    batch = prepare_news([article(title=""), article()])
    assert len(batch.items) == len(batch.rejected) == 1
    assert batch.duplicate_count == 0


def test_generator_input_is_normalized_sorted_and_not_mutated():
    records = [
        article(),
        article(id="news-2", url="https://example.com/2",
                published_at="2026-01-01T01:00:00Z"),
    ]
    original = deepcopy(records)
    batch = prepare_news(record for record in records)
    assert records == original
    assert [item.id for item in batch.items] == ["news-2", "news-1"]
    assert batch.items[1].title == "샘플 뉴스"
    assert batch.items[1].published_at.isoformat() == "2026-01-01T00:00:00+00:00"


def test_error_details_do_not_retain_input_values():
    batch = prepare_news([article(url="private-input-not-a-url")])
    assert len(batch.rejected) == 1
    assert "private-input-not-a-url" not in repr(batch.rejected)
    assert batch.rejected[0].errors == [{"field": "url", "code": "url_parsing"}]
