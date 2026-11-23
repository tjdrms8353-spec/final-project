import httpx
import pytest

from app.features.trends.collectors.rss import collect_rss, parse_feed, RssCollectionError


def feed(items):
    return ("<rss><channel>" + items + "</channel></rss>").encode()


def item(url="https://example.com/1", date="Wed, 18 Nov 2026 09:00:00 GMT"):
    return f"<item><title>News</title><link>{url}</link><pubDate>{date}</pubDate></item>"


def test_mapping_duplicate_invalid_date_and_limit():
    batch = parse_feed(feed(item() + item(url="https://example.com/1#top") + item(date="bad") + item(url="https://example.com/2")), limit=3)
    assert (batch.input_count, len(batch.items), batch.duplicate_count, len(batch.rejected)) == (3, 1, 1, 1)
    assert batch.items[0].source == "BBC News"
    assert batch.items[0].observed_at is None
    assert batch.items[0].published_at.isoformat() == "2026-11-18T09:00:00+00:00"


@pytest.mark.parametrize("payload,code", [
    (b"broken", "invalid_xml"), (b"<html/>", "invalid_feed"),
    (b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>', "unsafe_xml"),
])
def test_invalid_feeds(payload, code):
    with pytest.raises(RssCollectionError) as error:
        parse_feed(payload)
    assert error.value.code == code


def test_http_failure_has_no_retry():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, text="private")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RssCollectionError) as error:
            collect_rss(client=client)
    assert len(calls) == 1
    assert error.value.status_code == 429


def test_default_client_identifies_collector(monkeypatch):
    import app.features.trends.collectors.rss as rss
    seen = {}
    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, content=feed(item()))
    real_client = httpx.Client
    monkeypatch.setattr(rss.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    collect_rss()
    assert seen["ua"] == rss.USER_AGENT


def test_size_limit(monkeypatch):
    import app.features.trends.collectors.rss as rss
    monkeypatch.setattr(rss, "MAX_BYTES", 10)
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=feed(item())))) as client:
        with pytest.raises(RssCollectionError, match="response_too_large"):
            collect_rss(client=client)


def test_korean_feed_source_title_and_timezone():
    xml = '<rss><channel><item><title><![CDATA[한국어 AI 뉴스 & 기술]]></title><link>https://www.hankyung.com/article/1</link><pubDate>Wed, 18 Nov 2026 09:00:00 +0900</pubDate></item></channel></rss>'.encode()
    def handler(request):
        assert str(request.url) == "https://www.hankyung.com/feed/it"
        return httpx.Response(200, content=xml)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        batch = collect_rss(feed="hankyung-it", client=client)
    assert len(batch.items) == 1
    assert batch.items[0].source == "한국경제"
    assert batch.items[0].title == "한국어 AI 뉴스 & 기술"
    assert batch.items[0].published_at.isoformat() == "2026-11-18T00:00:00+00:00"


def test_iso_pubdate_and_dc_date():
    xml = ('<rss xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
           '<item><title>A</title><link>https://example.com/a</link><pubDate>2026-11-19T17:17:21+09:00</pubDate></item>'
           '<item><title>B</title><link>https://example.com/b</link><dc:date>2026-11-19T17:16:01+09:00</dc:date></item>'
           '<item><title>C</title><link>https://example.com/c</link><dc:date>2026-11-19T17:16:01</dc:date></item>'
           '</channel></rss>').encode()
    batch = parse_feed(xml, feed="ohmynews-all")
    assert [i.published_at.isoformat() for i in batch.items] == [
        "2026-11-19T08:17:21+00:00", "2026-11-19T08:16:01+00:00"]
    assert len(batch.rejected) == 1  # timezone-less date is not guessed


def test_observed_time_only_for_listed_feed():
    xml = feed("<item><title>No date</title><link>https://www.hani.co.kr/arti/1.html</link></item>")
    batch = parse_feed(xml, feed="hani-all")
    assert len(batch.items) == 1 and batch.items[0].published_at is None
    assert batch.items[0].observed_at.tzinfo is not None
    other = parse_feed(xml, feed="khan-all")
    assert len(other.items) == 0 and len(other.rejected) == 1


def test_summary_only_for_summary_feeds():
    xml = feed(item().replace("</item>", "<description><![CDATA[<p>AI  workers</p> worry]]></description></item>"))
    assert parse_feed(xml, feed="bbc-tech").items[0].summary == "AI workers worry"
    assert parse_feed(xml, feed="sbs-latest").items[0].summary == ""


def test_section_labels():
    section = parse_feed(feed(item()), feed="yna-politics")
    assert section.sections == {section.items[0].id: ["정치"]}
    xml = feed('<item><title>A</title><link>https://www.khan.co.kr/a</link>'
               '<pubDate>Wed, 18 Nov 2026 09:00:00 GMT</pubDate>'
               '<category> 사회  일반 </category><category>사회 일반</category><category>국제</category></item>')
    inline = parse_feed(xml, feed="khan-all")
    assert list(inline.sections.values()) == [["사회 일반", "국제"]]
    tagged = feed(item().replace("</item>", "<category>키워드</category></item>"))
    assert parse_feed(tagged, feed="sbs-latest").sections == {}


def test_unregistered_feed_never_requests():
    def forbidden(request):
        raise AssertionError("Unexpected network request")
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        with pytest.raises(ValueError, match="Unknown feed"):
            collect_rss(feed="https://unregistered.example/feed", client=client)
