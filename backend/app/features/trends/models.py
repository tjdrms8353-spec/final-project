"""Proposed news table; apply its migration only after team schema review."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    # Canonical URL SHA-256, shared across collection sources.
    url_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    # Persist UTC without timezone because MySQL DATETIME has no timezone.
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime)
    sort_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (Index("ix_news_articles_sort_at", "sort_at", "url_hash"),)


class CollectionRun(Base):
    __tablename__ = "news_collection_runs"
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    feed: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    owner_id: Mapped[str | None] = mapped_column(String(64))
    input_count: Mapped[int | None] = mapped_column(Integer)
    accepted_count: Mapped[int | None] = mapped_column(Integer)
    rejected_count: Mapped[int | None] = mapped_column(Integer)
    duplicate_count: Mapped[int | None] = mapped_column(Integer)
    inserted_count: Mapped[int | None] = mapped_column(Integer)
    existing_count: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(50))
    http_status: Mapped[int | None] = mapped_column(Integer)
    # Oldest dated item in the fetched feed (UTC). If it is later than the previous
    # successful run, articles published in between may have been missed.
    window_start_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (Index("ix_news_collection_runs_started", "started_at"),)


class NewsTranslation(Base):
    """Machine translation of an article's title/summary; originals stay in news_articles."""
    __tablename__ = "news_translations"
    url_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    lang: Mapped[str] = mapped_column(String(8), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(20))
    translated_at: Mapped[datetime] = mapped_column(DateTime)


class NewsArticleSection(Base):
    """Publisher-assigned section labels, kept verbatim (normalization is a later step)."""
    __tablename__ = "news_article_sections"
    url_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(100), primary_key=True)
    feed: Mapped[str] = mapped_column(String(50))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    __table_args__ = (Index("ix_news_article_sections_label", "label"),)
