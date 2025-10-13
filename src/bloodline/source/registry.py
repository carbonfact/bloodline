from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceType:
    name: str

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"SourceType({self.name})"


class SourceRegistry:
    def __init__(self, initial: Iterable[str] = ()) -> None:
        self._sources = {name: SourceType(name) for name in initial}

    @property
    def sources(self) -> list[SourceType]:
        return list(self._sources.values())

    def register(self, name: str) -> SourceType:
        if name in self._sources:
            raise ValueError(f"Source '{name}' is already registered.")
        source = SourceType(name)
        self._sources[name] = source
        return source

    def get(self, name: str) -> SourceType:
        if name not in self._sources:
            raise KeyError(f"Source '{name}' is not registered.")
        return self._sources[name]


_DEFAULTS_SOURCES = SourceRegistry(initial=("DATA_SOURCE", "HEURISTIC", "RULE", "HARD_CODING", "DATA_EXCHANGE"))


def get_source_registry() -> SourceRegistry:
    return _DEFAULTS_SOURCES


def set_source_registry(reg: SourceRegistry) -> None:
    global _DEFAULTS_SOURCES
    _DEFAULTS_SOURCES = reg
