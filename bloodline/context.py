"""Context shared between decorators and pandas hooks."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from .source import Source

__all__ = [
    "LineageRuntimeConfig",
    "get_lineage_context",
    "push_lineage_context",
    "pop_lineage_context",
    "temporary_lineage_context",
]


@dataclass(frozen=True)
class LineageRuntimeConfig:
    default_source: Source
    metadata: Mapping[str, Any] | None = None
    extra_sources_type: tuple[str, ...] = ()
    verbosity: bool = False


_LINEAGE_CONTEXT: ContextVar[LineageRuntimeConfig | None] = ContextVar("bloodline_lineage_context", default=None)


def get_lineage_context() -> LineageRuntimeConfig | None:
    return _LINEAGE_CONTEXT.get()


def push_lineage_context(config: LineageRuntimeConfig):
    return _LINEAGE_CONTEXT.set(config)


def pop_lineage_context(token) -> None:
    _LINEAGE_CONTEXT.reset(token)


@contextmanager
def temporary_lineage_context(config: LineageRuntimeConfig):
    token = push_lineage_context(config)
    try:
        yield
    finally:
        pop_lineage_context(token)
