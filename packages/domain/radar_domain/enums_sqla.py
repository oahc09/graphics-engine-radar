from __future__ import annotations

from sqlalchemy.types import Enum as SAEnum

from radar_domain.enums import (
    ChangeSignal,
    EventSourceRole,
    EventStatus,
    EventTopicRelation,
    EventType,
    ImpactLevel,
    MaturityStage,
    ObjectType,
    RawFilterStatus,
    SourceType,
    TrendState,
)


def pg_enum(name: str, enum_cls: type) -> SAEnum:
    # store enum *values* (e.g. "Notable", "Production"), not member names
    return SAEnum(enum_cls, name=name, native_enum=False, length=64,
                  validate_strings=True,
                  values_callable=lambda cls: [m.value for m in cls])


OBJECT_TYPE = pg_enum("object_type", ObjectType)
SOURCE_TYPE = pg_enum("source_type", SourceType)
RAW_FILTER_STATUS = pg_enum("raw_filter_status", RawFilterStatus)
EVENT_TYPE = pg_enum("event_type", EventType)
CHANGE_SIGNAL = pg_enum("change_signal", ChangeSignal)
EVENT_STATUS = pg_enum("event_status", EventStatus)
EVENT_SOURCE_ROLE = pg_enum("event_source_role", EventSourceRole)
EVENT_TOPIC_RELATION = pg_enum("event_topic_relation", EventTopicRelation)
IMPACT_LEVEL = pg_enum("impact_level", ImpactLevel)
MATURITY_STAGE = pg_enum("maturity_stage", MaturityStage)
TREND_STATE = pg_enum("trend_state", TrendState)

__all__ = [
    "OBJECT_TYPE",
    "SOURCE_TYPE",
    "RAW_FILTER_STATUS",
    "EVENT_TYPE",
    "CHANGE_SIGNAL",
    "EVENT_STATUS",
    "EVENT_SOURCE_ROLE",
    "EVENT_TOPIC_RELATION",
    "IMPACT_LEVEL",
    "MATURITY_STAGE",
    "TREND_STATE",
]
