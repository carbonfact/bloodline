"""Public decorator entry point for bloodline."""

from __future__ import annotations

import enum
import functools
from collections.abc import Callable, Iterable, Mapping
from typing import Any

import pandas as pd
from loguru import logger

from .apply import apply_data_lineage
from .context import LineageRuntimeConfig, temporary_lineage_context
from .pandas_hooks import pandas_lineage_patched
from .source import Source, SourceType

__all__ = ["Lineage", "data_lineage"]

Decorator = Callable[[Callable[..., pd.DataFrame]], Callable[..., pd.DataFrame]]


class DataFrameProtocol(enum.StrEnum):
    PANDAS = "pandas"


class Lineage:
    """Configurable decorator that scopes pandas lineage hooks.

    Instantiating this class captures a default source definition plus optional
    metadata/verbosity knobs. Using the instance as ``@lineage`` performs:

    1. Build a :class:`LineageRuntimeConfig` describing the active decorator
       (default source, extra source types, optional metadata).
    2. Install temporary pandas patches (``pd.read_csv``, ``pd.merge``, etc.).
    3. Execute the wrapped callable.
    4. Ensure the returned dataframe exposes a ``data_lineage`` column via
       :func:`apply_data_lineage`.

    This mirrors the design goal we use internally: zero boilerplate for
    everyday pandas flows, explicit overrides when you want to do something
    fancy.

    """

    def __init__(
        self,
        *,
        default_source: Source | None = None,
        extra_sources_type: Iterable[str] | None = None,
        verbosity: bool = False,
        dataframe_protocol: str = DataFrameProtocol.PANDAS,
    ) -> None:
        self.default_source = default_source or Source.hard_coded()
        self.extra_sources_type = tuple(extra_sources_type or ())
        self.verbosity = verbosity
        self.dataframe_protocol = DataFrameProtocol(dataframe_protocol)

    def __call__(self, func: Callable | None = None, *, metadata: Mapping[str, Any] | None = None):
        """Allow the instance itself to be used as ``@lineage``."""
        decorator = self._build_decorator(source=self.default_source, base_metadata=metadata)
        if func is None:
            return decorator
        return decorator(func)

    def with_source(self, *, source: str | Source | SourceType, metadata: Mapping[str, Any] | None = None):
        """Return a decorator bound to a specific ``source`` type/metadata."""
        override = self._coerce_source(source)
        return self._build_decorator(source=override, base_metadata=metadata)

    # ------------------------------------------------------------------

    def _build_decorator(self, source: Source, base_metadata: Mapping[str, Any] | None):
        """Combine metadata layers and produce the actual decorator."""

        def decorator(func: Callable | None = None, *, metadata: Mapping[str, Any] | None = None):
            combined_metadata = self._merge_metadata(base_metadata, metadata)
            effective_source = source if not combined_metadata else source.with_metadata(**combined_metadata)
            if func is None:
                return lambda actual: self._wrap(actual, effective_source, combined_metadata)
            return self._wrap(func, effective_source, combined_metadata)

        return decorator

    def _wrap(self, func: Callable, default_source: Source, metadata: Mapping[str, Any] | None):
        """Install patches, run ``func``, and normalize return values."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            runtime_config = LineageRuntimeConfig(
                default_source=default_source,
                metadata=metadata,
                extra_sources_type=self.extra_sources_type,
                verbosity=self.verbosity,
            )

            patch = {
                DataFrameProtocol.PANDAS: pandas_lineage_patched,
            }

            with patch[self.dataframe_protocol](), temporary_lineage_context(runtime_config):
                result = func(*args, **kwargs)

            if not isinstance(result, pd.DataFrame):
                logger.warning(
                    f"Lineage decorator expected a pandas DataFrame from '{func.__name__}'; lineage was not updated.",
                )
                return result

            return apply_data_lineage(result, default_source=default_source)

        return wrapper

    @staticmethod
    def _merge_metadata(
        base: Mapping[str, Any] | None,
        override: Mapping[str, Any] | None,
    ) -> Mapping[str, Any] | None:
        if not base and not override:
            return None
        merged: dict[str, Any] = {}
        if base:
            merged.update(base)
        if override:
            merged.update(override)
        return merged

    @staticmethod
    def _coerce_source(source: str | Source | SourceType) -> Source:
        """Normalize user input into a :class:`Source` instance."""
        if isinstance(source, Source):
            return source
        if isinstance(source, SourceType):
            return Source(source_type=source)
        return Source(source_type=str(source))


def data_lineage(*args, **kwargs) -> Lineage:
    """Compatibility helper mirroring Vera's decorator naming."""
    return Lineage(*args, **kwargs)
