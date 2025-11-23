import dataclasses
import enum


class RelationshipType(enum.StrEnum):
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    MANY_TO_MANY = "MANY_TO_MANY"


@dataclasses.dataclass(frozen=True, kw_only=True, eq=True)
class Relationship:
    left_name: str
    left_key: tuple[str, ...]
    right_name: str
    right_key: tuple[str, ...]
    relationship_type: RelationshipType
