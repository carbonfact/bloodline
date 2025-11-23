"""Core lineage primitives (SourceType + Source)."""

from __future__ import annotations

import dataclasses
import enum
from typing import Any

__all__ = ["SourceType", "Source", "SourceMetadata"]


class SourceType(enum.Enum):
    """Fixed taxonomy available in the OSS package."""

    DATA_SOURCE = "DATA_SOURCE"
    UNKNOWN = "UNKNOWN"


SourceMetadata = dict[str, Any]


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Source:
    """Represents the provenance of a single data point."""

    source_type: str | SourceType
    source_metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.source_type, SourceType):
            object.__setattr__(self, "source_type", self.source_type.value)

    @staticmethod
    def data_source(**metadata: Any) -> Source:
        return Source(source_type=SourceType.DATA_SOURCE, source_metadata=dict(metadata))

    @staticmethod
    def unknown(**metadata: Any) -> Source:
        return Source(source_type=SourceType.UNKNOWN, source_metadata=dict(metadata))

    def with_metadata(self, **metadata: Any) -> Source:
        merged = dict(self.source_metadata)
        merged.update(metadata)
        return Source(source_type=self.source_type, source_metadata=merged)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_metadata": dict(self.source_metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Source:
        return cls(
            source_type=payload["source_type"],
            source_metadata=dict(payload.get("source_metadata", {})),
        )
