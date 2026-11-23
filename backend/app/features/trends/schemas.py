from datetime import timezone
from typing import Literal

from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator,
    model_validator,
)


class NewsItem(BaseModel):
    """원본 기사 응답. 순위·감성·언급량 등 분석 결과는 포함하지 않습니다.

    published_at 또는 observed_at 중 하나 이상이 필요합니다.
    DB 저장 구조는 이 API 모델과 별도로 팀 협의 후 결정합니다.
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: str = Field(min_length=1, description="기사 식별자. 샘플과 수집 출처별 ID를 구분합니다.")
    title: str = Field(min_length=1, description="공백을 정규화한 기사 제목")
    url: HttpUrl = Field(description="HTTP 또는 HTTPS 원문 주소")
    source: str = Field(min_length=1, description="출처 이름 또는 도메인. 수집 제공자 이름과 다를 수 있습니다.")
    published_at: AwareDatetime | None = Field(
        default=None, description="확인된 기사 발행 시각(UTC). 알 수 없으면 null이며 관측 시각으로 대체하지 않습니다.",
    )
    observed_at: AwareDatetime | None = Field(
        default=None, description="수집 출처가 기사를 관측한 시각(UTC). 알 수 없으면 null입니다.",
    )
    summary: str = Field(default="", description="제공된 요약문. 없으면 빈 문자열이며 AI 요약을 의미하지 않습니다.")

    @field_validator("title", "summary", mode="before")
    @classmethod
    def normalize_text(cls, value):
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @field_validator("published_at", "observed_at")
    @classmethod
    def normalize_time(cls, value):
        return value.astimezone(timezone.utc) if value is not None else None

    @model_validator(mode="after")
    def require_timestamp(self):
        if self.published_at is None and self.observed_at is None:
            raise ValueError("A publication or observation timestamp is required")
        return self


class SampleNewsResponse(BaseModel):
    data_source: Literal["sample"] = Field(default="sample", description="가상 데이터 표시. 실시간 수집 결과가 아닙니다.")
    items: list[NewsItem]
    total: int = Field(ge=0, description="limit 적용 전 샘플 기사 수. 현재 반환된 items 길이와 다를 수 있습니다.")


class StoredNewsItem(NewsItem):
    article_id: str = Field(description="상세 조회용 고유 ID(URL SHA-256). id는 원래 수집 출처의 ID입니다.")
    title_ko: str | None = Field(default=None, description="해외 기사의 한국어 기계 번역 제목. 번역 전·국내 기사는 null")
    summary_ko: str | None = Field(default=None, description="해외 기사의 한국어 기계 번역 요약. 번역 전·국내 기사는 null")


class CoverageGap(BaseModel):
    feed: str = Field(description="수집 출처 키 (예: yna-all)")
    start: AwareDatetime = Field(description="공백 시작(UTC): 직전 성공 수집 시각")
    end: AwareDatetime | None = Field(description="공백 끝(UTC). ongoing이면 null")
    kind: Literal["missed", "unverified", "ongoing"] = Field(
        description="missed: 피드 보관 범위가 직전 수집과 이어지지 않아 기사 누락 가능 / "
                    "unverified: 보관 범위 기록이 없고 간격이 김 / ongoing: 최근 수집이 멈춤")


class CoverageResponse(BaseModel):
    since: AwareDatetime
    gaps: list[CoverageGap]


class NewsListResponse(BaseModel):
    data_source: Literal["database"] = "database"
    items: list[StoredNewsItem]
    total: int = Field(ge=0, description="검색·출처 필터 적용 후, 페이지 제한 전 개수")
    limit: int
    offset: int
