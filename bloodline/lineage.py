"""Public decorator entry point for bloodline."""

from __future__ import annotations

import enum
import functools
import typing
from collections.abc import Callable, Iterable, Mapping

import pandas as pd
from loguru import logger

from . import erd
from .apply import apply_data_lineage
from .context import LineageRuntimeConfig, temporary_lineage_context
from .pandas_hooks import pandas_lineage_patched
from .source import Source, SourceType

__all__ = ["Lineage"]

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
        self.default_source = default_source or Source.unknown()
        self.extra_sources_type = tuple(extra_sources_type or ())
        self.verbosity = verbosity
        self.dataframe_protocol = DataFrameProtocol(dataframe_protocol)
        self.erd = erd.EntityRelationshipDiagram()

    def __call__(
        self,
        func: Callable | None = None,
        *,
        metadata: Mapping[str, typing.Any] | None = None,
        return_arg: typing.Hashable | None = None,
        inheritance: dict[str, str] | None = None,
    ):
        """Allow the instance itself to be used as ``@lineage``."""
        decorator = self._build_decorator(
            source=self.default_source,
            base_metadata=metadata,
            return_arg=return_arg,
            inheritance=inheritance,
        )
        if func is None:
            return decorator
        return decorator(func)

    def with_source(
        self,
        *,
        source: str | Source | SourceType,
        metadata: Mapping[str, typing.Any] | None = None,
        return_arg: typing.Hashable | None = None,
        inheritance: dict[str, str] | None = None,
    ):
        """Return a decorator bound to a specific ``source`` type/metadata."""
        override = self._coerce_source(source)
        return self._build_decorator(
            source=override,
            base_metadata=metadata,
            return_arg=return_arg,
            inheritance=inheritance,
        )

    # ------------------------------------------------------------------

    def _build_decorator(
        self,
        source: Source,
        base_metadata: Mapping[str, typing.Any] | None,
        return_arg: typing.Hashable | None,
        inheritance: dict[str, str] | None = None,
    ):
        """Combine metadata layers and produce the actual decorator."""

        def decorator(
            func: Callable | None = None,
            *,
            metadata: Mapping[str, typing.Any] | None = None,
            return_arg: typing.Hashable | None = return_arg,
        ):
            combined_metadata = self._merge_metadata(base=base_metadata, override=metadata)
            effective_source = source if not combined_metadata else source.with_metadata(**combined_metadata)
            if func is None:
                return lambda actual: self._wrap(
                    func=actual,
                    default_source=effective_source,
                    metadata=combined_metadata,
                    return_arg=return_arg,
                    inheritance=inheritance,
                )
            return self._wrap(
                func=func,
                default_source=effective_source,
                metadata=combined_metadata,
                return_arg=return_arg,
                inheritance=inheritance,
            )

        return decorator

    def _handle_detected_relationship(self, relationship: erd.Relationship) -> None:
        self.erd.add(relationship)

    def _wrap(
        self,
        func: Callable,
        default_source: Source,
        metadata: Mapping[str, typing.Any] | None,
        return_arg: typing.Hashable | None,
        inheritance: dict[str, str] | None = None,
    ) -> typing.Callable:
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
            }[self.dataframe_protocol]

            with (
                patch(detected_relationship_hook=self._handle_detected_relationship),
                temporary_lineage_context(runtime_config),
            ):
                result = func(*args, **kwargs)

            table = result[return_arg] if return_arg is not None else result
            if not isinstance(table, pd.DataFrame):
                logger.warning(
                    f"Lineage decorator expected a dataframe from '{func}'; lineage was not updated.",
                )
                return result

            table_with_lineage = apply_data_lineage(table, default_source=default_source, inheritance=inheritance)
            if return_arg is not None:
                if isinstance(result, tuple):
                    result_as_list = list(result)
                    result_as_list[return_arg] = table_with_lineage  # type: ignore
                    return tuple(result_as_list)
                elif isinstance(result, dict):
                    result[return_arg] = table_with_lineage
                    return result
                else:
                    logger.warning(
                        f"Lineage decorator expected a tuple or dict when using 'return_arg' in '{func}'; "
                        "lineage was not updated.",
                    )
                    return result
            else:
                return table_with_lineage

        return wrapper

    @staticmethod
    def _merge_metadata(
        base: Mapping[str, typing.Any] | None,
        override: Mapping[str, typing.Any] | None,
    ) -> Mapping[str, typing.Any] | None:
        if not base and not override:
            return None
        merged: dict[str, typing.Any] = {}
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
