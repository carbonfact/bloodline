"""Generic helpers reused across modules."""

from __future__ import annotations

import typing

import pandas as pd

from .constants import DATA_LINEAGE_COLUMN


def is_empty(value) -> bool:
    """Return True when the value should not emit lineage (None, NaN, empty collection)."""
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, (set, list, tuple)) and not value:
        return True
    if isinstance(value, pd.Series):
        return bool(value.isna().all())
    return False


def ensure_lineage_column(table: pd.DataFrame) -> pd.DataFrame:
    """Guarantee the dataframe slice owns a `data_lineage` column with dict rows."""
    if DATA_LINEAGE_COLUMN in table.columns:
        return table

    table[DATA_LINEAGE_COLUMN] = [{} for _ in range(len(table))]
    return table


def to_dict_fast(df: pd.DataFrame) -> typing.Generator[dict, None, None]:
    """Fast version of df.to_dict(orient="records").

    Same as df.to_dict(orient="records"), but faster (and probably less safe!)

    This is purely for performance reasons. For example, sometimes we loop over long BoMs of
    several hundreds of thousands rows, and the to_dict(orient="records") method is quite slow in
    such a case.

    🐲 There is very little reason to use this function. It's only used in core code to speed
    hot paths. Don't use it for account parsers, because it's probably not worth it.

    """
    columns = df.columns.tolist()
    # 🐅: we have to do .astype(object) so that NA frienly types (e.g. pd.Int64Dtype()) accept
    # to replace pd.NA with None.
    # Memory optimization: use inplace=True to avoid creating a copy during replace
    df_obj = df.astype(object)
    df_obj.replace(to_replace=pd.NA, value=None, inplace=True)
    for row in df_obj.values:
        yield dict(zip(columns, row, strict=True))
