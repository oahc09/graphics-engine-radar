from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from radar_domain.enums import (
    EventSourceRole,
    EventStatus,
    EventType,
    ImpactLevel,
    MaturityStage,
    RawFilterStatus,
    TrendState,
)
from radar_domain.enums_sqla import (
    CHANGE_SIGNAL,
    EVENT_SOURCE_ROLE,
    EVENT_STATUS,
    EVENT_TOPIC_RELATION,
    EVENT_TYPE,
    IMPACT_LEVEL,
    MATURITY_STAGE,
    OBJECT_TYPE,
    RAW_FILTER_STATUS,
    SOURCE_TYPE,
    TREND_STATE,
)
from radar_domain.settings import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class Object(Base):
    __tablename__ = "objects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    type: Mapped[str] = mapped_column(OBJECT_TYPE)
    domain: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    official_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_repo: Mapped[str | None] = mapped_column(String(256), nullable=True)
    aliases: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow
    )

    sources: Mapped[list["Source"]] = relationship(back_populates="object")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("objects.id"), index=True)
    type: Mapped[str] = mapped_column(SOURCE_TYPE)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    adapter: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=120)
    last_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow
    )

    object: Mapped[Object] = relationship(back_populates="sources")
    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")


class RawItem(Base):
    __tablename__ = "raw_items"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_rawitem_source_external"),
        Index("ix_rawitem_canonical_url", "canonical_url"),
        Index("ix_rawitem_filter_status", "filter_status"),
        Index("ix_rawitem_content_hash", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    filter_status: Mapped[str] = mapped_column(
        RAW_FILTER_STATUS, default=RawFilterStatus.NEW.value, index=True
    )
    filter_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[Source] = relationship(back_populates="raw_items")
    event_links: Mapped[list["EventSource"]] = relationship(back_populates="raw_item")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_status", "status"),
        Index("ix_events_published_at", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(256), unique=True, index=True)

    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")

    event_type: Mapped[str] = mapped_column(EVENT_TYPE)
    change_signal: Mapped[str] = mapped_column(CHANGE_SIGNAL)

    change: Mapped[str] = mapped_column(Text, default="")
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    who_should_care: Mapped[str] = mapped_column(Text, default="")

    impact_level: Mapped[str] = mapped_column(IMPACT_LEVEL, default=ImpactLevel.NOTABLE.value)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    # internal 0..5 five-dimension scores (spec §17): never shown as a fake /100
    impact_capability: Mapped[int] = mapped_column(Integer, default=0)
    impact_engineering: Mapped[int] = mapped_column(Integer, default=0)
    impact_adoption: Mapped[int] = mapped_column(Integer, default=0)
    impact_scope: Mapped[int] = mapped_column(Integer, default=0)
    impact_confidence: Mapped[int] = mapped_column(Integer, default=0)

    maturity_from: Mapped[str | None] = mapped_column(MATURITY_STAGE, nullable=True)
    maturity_to: Mapped[str | None] = mapped_column(MATURITY_STAGE, nullable=True)

    object_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objects.id"), nullable=True, index=True
    )

    title_embedding: Mapped[list | None] = mapped_column(
        Vector(get_settings().llm_embedding_dim), nullable=True
    )
    change_embedding: Mapped[list | None] = mapped_column(
        Vector(get_settings().llm_embedding_dim), nullable=True
    )

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow
    )

    status: Mapped[str] = mapped_column(
        EVENT_STATUS, default=EventStatus.CANDIDATE.value, index=True
    )

    object: Mapped[Object | None] = relationship()
    sources: Mapped[list["EventSource"]] = relationship(back_populates="event")
    topics: Mapped[list["EventTopic"]] = relationship(back_populates="event")


class EventSource(Base):
    __tablename__ = "event_sources"
    __table_args__ = (
        UniqueConstraint("event_id", "raw_item_id", name="uq_eventsource_event_rawitem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    raw_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_items.id"), index=True)
    role: Mapped[str] = mapped_column(EVENT_SOURCE_ROLE)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    event: Mapped[Event] = relationship(back_populates="sources")
    raw_item: Mapped[RawItem] = relationship(back_populates="event_links")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    parent_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    aliases: Mapped[list] = mapped_column(JSONB, default=list)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)

    events: Mapped[list["EventTopic"]] = relationship(back_populates="topic")


class EventTopic(Base):
    __tablename__ = "event_topics"
    __table_args__ = (
        UniqueConstraint("event_id", "topic_id", name="uq_eventtopic_event_topic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    relation: Mapped[str] = mapped_column(EVENT_TOPIC_RELATION, default="direct")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    event: Mapped[Event] = relationship(back_populates="topics")
    topic: Mapped[Topic] = relationship(back_populates="events")


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"
    __table_args__ = (
        UniqueConstraint("topic_id", "window_days", "snapshot_date", name="uq_trend_topic_window"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    window_days: Mapped[int] = mapped_column(Integer)  # 30 or 90
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event_count: Mapped[int] = mapped_column(Integer, default=0)
    important_event_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_object_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_vendor_count: Mapped[int] = mapped_column(Integer, default=0)
    platform_expansion_count: Mapped[int] = mapped_column(Integer, default=0)
    maturity_transition_count: Mapped[int] = mapped_column(Integer, default=0)
    adoption_count: Mapped[int] = mapped_column(Integer, default=0)

    state: Mapped[str] = mapped_column(TREND_STATE, default=TrendState.STABLE.value)

    topic: Mapped[Topic] = relationship()


class DailyDigest(Base):
    __tablename__ = "digests"
    __table_args__ = (
        UniqueConstraint("kind", "date", name="uq_digest_kind_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    kind: Mapped[str] = mapped_column(String(16))  # daily | weekly | monthly
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    title: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    event_ids: Mapped[list] = mapped_column(JSONB, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIExecution(Base):
    """Traceability record for every AI/heuristic judgment (spec §36)."""

    __tablename__ = "ai_executions"
    __table_args__ = (Index("ix_ai_executions_stage", "pipeline_stage"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    pipeline_stage: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(32))
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
