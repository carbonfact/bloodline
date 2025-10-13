import dataclasses
from typing import Any

from .registry import SourceType, get_source_registry, set_source_registry

__all__ = ["Source", "get_source_registry", "set_source_registry"]

SourceMetadata = dict[str, Any]
DataLineage = dict[str, dict[str, Any]]


# NOTE(alexis): using slogs to reduce memory usage
# and prevents accidental attributes creation.
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Source:
    source_type: SourceType
    source_metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    @staticmethod
    def data_source(**meta) -> "Source":
        return Source(source_type=get_source_registry().get("DATA_SOURCE"), source_metadata=meta)

    @staticmethod
    def heuristic(**meta) -> "Source":
        return Source(source_type=get_source_registry().get("HEURISTIC"), source_metadata=meta)

    @staticmethod
    def rule(**meta) -> "Source":
        return Source(source_type=get_source_registry().get("RULE"), source_metadata=meta)

    def to_dict(self) -> dict[str, Any]:
        return {"source_type": self.source_type.name, "source_metadata": self.source_metadata}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Source":
        return cls(
            source_type=get_source_registry().get(d["source_type"]),
            source_metadata=d.get("source_metadata", {}),
        )
