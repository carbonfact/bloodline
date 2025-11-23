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
    left_key: str
    right_name: str
    right_key: str
    relationship_type: RelationshipType


class EntityRelationshipDiagram:
    def __init__(self) -> None:
        self.relationships: set[Relationship] = set()

    def add(self, relationship: Relationship) -> None:
        if relationship.relationship_type == RelationshipType.MANY_TO_ONE:
            inverse = Relationship(
                left_name=relationship.right_name,
                left_key=relationship.right_key,
                right_name=relationship.left_name,
                right_key=relationship.left_key,
                relationship_type=RelationshipType.ONE_TO_MANY,
            )
            self.relationships.add(inverse)
        else:
            self.relationships.add(relationship)

    def to_mermaid(self) -> str:
        lines = ["erDiagram"]
        relationship_symbols = {
            RelationshipType.ONE_TO_ONE: "||--||",
            RelationshipType.ONE_TO_MANY: "||--o{",
            RelationshipType.MANY_TO_ONE: "o{--||",
            RelationshipType.MANY_TO_MANY: "o{--o{",
        }
        for rel in sorted(self.relationships, key=lambda r: (r.left_name, r.right_name, r.left_key, r.right_key)):
            symbol = relationship_symbols[rel.relationship_type]
            label = f"{rel.left_key} -> {rel.right_key}"
            lines.append(f'    "{rel.left_name}" {symbol} "{rel.right_name}" : "{label}"')
        return "\n".join(lines)
