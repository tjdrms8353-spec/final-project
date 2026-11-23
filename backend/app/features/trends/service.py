"""Local sample news only; no collection, database access or AI processing."""

from app.features.trends.preprocessing.news import prepare_news
from app.features.trends.schemas import SampleNewsResponse


def get_sample_news(limit: int = 20) -> SampleNewsResponse:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    # Fictional records for API integration, not actual news or popularity data.
    records = [
        {
            "id": "sample-001",
            "title": "샘플: 지역 도서관 디지털 교육 안내",
            "url": "https://example.com/news/sample-001",
            "source": "샘플 뉴스",
            "published_at": "2026-01-01T10:00:00+09:00",
            "summary": "실제 기사와 관계없는 개발용 샘플입니다.",
        },
        {
            "id": "sample-002",
            "title": "샘플: 친환경 교통 연구 소식",
            "url": "https://example.com/news/sample-002",
            "source": "샘플 뉴스",
            "published_at": "2026-01-01T09:00:00+09:00",
            "summary": "실제 기사와 관계없는 개발용 샘플입니다.",
        },
        {
            "id": "sample-003",
            "title": "샘플: 지역 문화 행사 안내",
            "url": "https://example.com/news/sample-003",
            "source": "샘플 뉴스",
            "published_at": "2026-01-01T08:00:00+09:00",
            "summary": "실제 기사와 관계없는 개발용 샘플입니다.",
        },
    ]
    batch = prepare_news(records)
    if batch.rejected or batch.duplicate_count:
        raise ValueError("Sample news fixtures must be valid and unique")
    return SampleNewsResponse(items=batch.items[:limit], total=len(batch.items))


def get_status():
    """Scaffold only; domain logic has not been implemented."""
    return {"feature": "trends", "status": "not_implemented"}
