"""Pandas accessor overrides installed temporarily by Lineage."""

from __future__ import annotations

import itertools
import typing
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
from loguru import logger

from . import erd
from .apply import apply_data_lineage
from .constants import DATA_LINEAGE_COLUMN
from .context import get_lineage_context
from .source import Source
from .tracking import is_data_lineage_tracked

OriginalFunction = Callable[..., typing.Any]


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
            if self._original_read_csv is None:
                raise RuntimeError("Original 'read_csv' function is not defined.")
            df = self._original_read_csv(*args, **kwargs)
            return self._tag_data_source(df, args, kwargs)

        def wrapped_read_excel(*args, **kwargs):
            if self._original_read_excel is None:
                raise RuntimeError("Original 'read_excel' function is not defined.")
            df = self._original_read_excel(*args, **kwargs)
            return self._tag_data_source(df, args, kwargs)

        def wrapped_merge(left, right, *args, **kwargs):
            if self._original_merge is None:
                raise RuntimeError("Original 'merge' function is not defined.")
            inheritance = kwargs.pop("_lineage_inheritance", None)
            merged = self._original_merge(left, right, *args, **kwargs)
            merged = fuse_data_lineage_columns(merged)

            if (left_on := kwargs.get("left_on") or kwargs.get("on") or (args[2] if len(args) > 2 else None)) is None:
                logger.warning("Unable to detect 'right_on' key for lineage relationship generation in pd.merge")
            if (right_on := kwargs.get("right_on") or kwargs.get("on") or (args[3] if len(args) > 3 else None)) is None:
                logger.warning("Unable to detect 'right_on' key for lineage relationship generation in pd.merge")
            if left_on is not None and right_on is not None:
                for relationship in _generate_relationships_between_tables(
                    left=left, left_on=left_on, right=right, right_on=right_on
                ):
                    detected_relationship_hook(relationship)

            return apply_data_lineage(
                merged,
                default_source=_active_default_source(),
                inheritance=inheritance,
            )

        def wrapped_join(self_df, other, *args, **kwargs):
            if self._original_join is None:
                raise RuntimeError("Original 'join' function is not defined.")
            inheritance = kwargs.pop("_lineage_inheritance", None)
            joined = self._original_join(self_df, other, *args, **kwargs)
            joined = fuse_data_lineage_columns(joined)

            if (left_on := kwargs.get("left_on") or kwargs.get("on") or (args[2] if len(args) > 2 else None)) is None:
                logger.warning("Unable to detect 'right_on' key for lineage relationship generation in pd.merge")
            if (right_on := kwargs.get("right_on") or kwargs.get("on") or (args[3] if len(args) > 3 else None)) is None:
                logger.warning("Unable to detect 'right_on' key for lineage relationship generation in pd.merge")
            if left_on is not None and right_on is not None:
                for relationship in _generate_relationships_between_tables(
                    left=self_df,
                    left_on=left_on,
                    right=other,
                    right_on=right_on,
                ):
                    detected_relationship_hook(relationship)

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
    def _tag_data_source(df: pd.DataFrame, args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any]):
        if not is_data_lineage_tracked():
            return df

        filepath = PandasHookManager._extract_path(args, kwargs)
        source = Source.data_source(file_path=str(filepath) if filepath else None)
        return apply_data_lineage(df, default_source=source)

    @staticmethod
    def _extract_path(args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any]):
        # TODO: handle Excel sheet name
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
    return ctx.default_source if ctx else Source.unknown()


def _list_tables_in_data_lineage(table: pd.DataFrame, join_key: str) -> list[str]:
    if DATA_LINEAGE_COLUMN not in table.columns:
        return []
    return table[DATA_LINEAGE_COLUMN].str[join_key].str["source_metadata"].str["file_path"].unique().tolist()  # type: ignore


def _generate_relationships_between_tables(
    left: pd.DataFrame,
    left_on: str | tuple[str, ...],
    right: pd.DataFrame,
    right_on: str | tuple[str, ...],
) -> typing.Generator[erd.Relationship]:
    left_keys = [left_on] if isinstance(left_on, str | int) else list(left_on)
    right_keys = [right_on] if isinstance(right_on, str | int) else list(right_on)

    for left_key, right_key in itertools.product(left_keys, right_keys):
        for left_table, right_table in itertools.product(
            _list_tables_in_data_lineage(table=left, join_key=left_key),
            _list_tables_in_data_lineage(table=right, join_key=right_key),
        ):
            # TODO: is this ok in terms of performance?
            is_left_unique = left.duplicated(subset=[left_key]).sum() == 0
            is_right_unique = right.duplicated(subset=[right_key]).sum() == 0
            if is_left_unique and is_right_unique:
                relationship_type = erd.RelationshipType.ONE_TO_ONE
            elif is_left_unique and not is_right_unique:
                relationship_type = erd.RelationshipType.ONE_TO_MANY
            elif not is_left_unique and is_right_unique:
                relationship_type = erd.RelationshipType.MANY_TO_ONE
            else:
                relationship_type = erd.RelationshipType.MANY_TO_MANY
            yield erd.Relationship(
                left_name=left_table,
                left_key=left_key,
                right_name=right_table,
                right_key=right_key,
                relationship_type=relationship_type,
            )
