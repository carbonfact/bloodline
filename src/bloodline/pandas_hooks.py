"""Pandas accessor overrides installed temporarily by Lineage."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

from . import erd
from .apply import apply_data_lineage
from .constants import DATA_LINEAGE_COLUMN
from .context import get_lineage_context
from .source import Source
from .tracking import is_data_lineage_tracked

OriginalFunction = Callable[..., Any]


def fuse_data_lineage_columns(df: pd.DataFrame) -> pd.DataFrame:
    data_lineage_columns = [col for col in df.columns if isinstance(col, str) and col.startswith(DATA_LINEAGE_COLUMN)]
    if len(data_lineage_columns) <= 1:
        return df

    fused = []
    for _, row in df.iterrows():
        merged = {}
        for column in data_lineage_columns:
            payload = row[column]
            if isinstance(payload, dict):
                merged.update(payload)
        fused.append(merged)

    result = df.copy()
    result[DATA_LINEAGE_COLUMN] = fused
    drop_columns = [col for col in data_lineage_columns if col != DATA_LINEAGE_COLUMN]
    return result.drop(columns=drop_columns)


class PandasHookManager:
    """Installs lineage-aware shims around pandas calls."""

    def __init__(self) -> None:
        self._stack_depth = 0
        self._original_read_csv: OriginalFunction | None = None
        self._original_read_excel: OriginalFunction | None = None
        self._original_merge: OriginalFunction | None = None
        self._original_join: OriginalFunction | None = None

    def install(self, detected_relationship_hook: Callable[[erd.Relationship], None]) -> None:
        if self._stack_depth == 0:
            self._patch(detected_relationship_hook=detected_relationship_hook)
        self._stack_depth += 1

    def uninstall(self) -> None:
        if self._stack_depth == 0:
            return
        self._stack_depth -= 1
        if self._stack_depth == 0:
            self._restore()

    def _patch(self, detected_relationship_hook: Callable[[erd.Relationship], None]) -> None:
        self._original_read_csv = pd.read_csv
        self._original_read_excel = pd.read_excel
        self._original_merge = pd.merge
        self._original_join = pd.DataFrame.join

        def wrapped_read_csv(*args, **kwargs):
            df = self._original_read_csv(*args, **kwargs)
            return self._tag_data_source(df, args, kwargs)

        def wrapped_read_excel(*args, **kwargs):
            df = self._original_read_excel(*args, **kwargs)
            return self._tag_data_source(df, args, kwargs)

        def wrapped_merge(left, right, *args, **kwargs):
            inheritance = kwargs.pop("_lineage_inheritance", None)
            merged = self._original_merge(left, right, *args, **kwargs)
            merged = fuse_data_lineage_columns(merged)
            return apply_data_lineage(
                merged,
                default_source=_active_default_source(),
                inheritance=inheritance,
            )

        def wrapped_join(self_df, other, *args, **kwargs):
            inheritance = kwargs.pop("_lineage_inheritance", None)
            joined = self._original_join(self_df, other, *args, **kwargs)
            joined = fuse_data_lineage_columns(joined)
            return apply_data_lineage(
                joined,
                default_source=_active_default_source(),
                inheritance=inheritance,
            )

        pd.read_csv = wrapped_read_csv  # type: ignore
        pd.read_excel = wrapped_read_excel  # type: ignore
        pd.merge = wrapped_merge  # type: ignore
        pd.DataFrame.merge = wrapped_merge  # type: ignore
        pd.DataFrame.join = wrapped_join  # type: ignore

    def _restore(self) -> None:
        if self._original_read_csv is not None:
            pd.read_csv = self._original_read_csv  # type: ignore
        if self._original_read_excel is not None:
            pd.read_excel = self._original_read_excel  # type: ignore
        if self._original_merge is not None:
            pd.merge = self._original_merge  # type: ignore
            pd.DataFrame.merge = self._original_merge  # type: ignore
        if self._original_join is not None:
            pd.DataFrame.join = self._original_join  # type: ignore

    @staticmethod
    def _tag_data_source(df: pd.DataFrame, args: tuple[Any, ...], kwargs: dict[str, Any]):
        if not is_data_lineage_tracked():
            return df

        filepath = PandasHookManager._extract_path(args, kwargs)
        source = Source.data_source(file_path=str(filepath) if filepath else None)
        return apply_data_lineage(df, default_source=source)

    @staticmethod
    def _extract_path(args: tuple[Any, ...], kwargs: dict[str, Any]):
        if args:
            candidate = args[0]
        else:
            candidate = kwargs.get("path_or_buf") or kwargs.get("io")
        if isinstance(candidate, (str, Path)):
            return candidate
        return None


HOOK_MANAGER = PandasHookManager()


@contextmanager
def pandas_lineage_patched(detected_relationship_hook: Callable[[erd.Relationship], None]):
    HOOK_MANAGER.install(detected_relationship_hook=detected_relationship_hook)
    try:
        yield
    finally:
        HOOK_MANAGER.uninstall()


def _active_default_source() -> Source:
    ctx = get_lineage_context()
    return ctx.default_source if ctx else Source.hard_coded()
