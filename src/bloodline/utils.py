"""Generic helpers reused across modules."""

from __future__ import annotations

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
        return value.isna().all()
    return False


def ensure_lineage_column(table: pd.DataFrame) -> pd.DataFrame:
    """Guarantee the dataframe slice owns a `data_lineage` column with dict rows."""
    if DATA_LINEAGE_COLUMN in table.columns:
        return table

    table[DATA_LINEAGE_COLUMN] = [{} for _ in range(len(table))]
    return table
