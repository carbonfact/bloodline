import pandas as pd
from pandas.api.extensions import register_dataframe_accessor

from ..constants import DATA_LINEAGE_COLUMN
from ..core import DEFAULT_SOURCE, update_table_data_lineage

__all__ = ["LineageAccessor"]


def fuse_data_lineage_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    If a merge produced multiple lineage columns (e.g., data_lineage_x, data_lineage_y),
    fuse them into a single DATA_LINEAGE_COLUMN. Later values (right) take precedence.
    """
    cols = [c for c in df.columns if isinstance(c, str) and c.startswith(DATA_LINEAGE_COLUMN)]
    if len(cols) <= 1:
        return df

    def as_dict(x):
        return x if isinstance(x, dict) else {}

    fused = []
    for _, row in df.iterrows():
        merged = {}
        for col in cols:  # left-to-right; last wins
            merged.update(as_dict(row[col]))
        fused.append(merged)

    out = df.copy()
    out[DATA_LINEAGE_COLUMN] = fused
    # Drop extra DL columns but keep the canonical one
    to_drop = [c for c in cols if c != DATA_LINEAGE_COLUMN]
    return out.drop(columns=to_drop)


def lineage_merge(left: pd.DataFrame, right: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
    """
    Safer, explicit merge:
        1. pd.merge(...)
        2. fuse lineage columns if both sides have DATA_LINEAGE_COLUMN
        3. re-impute lineage for new columns using optional `_lineage_inheritance` (e.g., {"new_col": "parent_col"})
    """
    inheritance = kwargs.pop("_lineage_inheritance", None)
    merged = pd.merge(left, right, *args, **kwargs)
    merged = fuse_data_lineage_columns(merged)
    return update_table_data_lineage(merged, inheritance=inheritance, default_source=DEFAULT_SOURCE)


def lineage_join(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *args,
    **kwargs,
) -> pd.DataFrame:
    """
    Safer, explicit join:
        1. pd.DataFrame.join(...)
        2. fuse lineage columns if both sides have DATA_LINEAGE_COLUMN
        3. re-impute lineage for new columns using optional `_lineage_inheritance` (e.g., {"new_col": "parent_col"})
    """
    inheritance = kwargs.pop("_lineage_inheritance", None)
    joined = left.join(right, *args, **kwargs)
    joined = fuse_data_lineage_columns(joined)
    return update_table_data_lineage(joined, inheritance=inheritance, default_source=DEFAULT_SOURCE)


@register_dataframe_accessor("lineage")
class LineageAccessor:
    def __init__(self, pandas_obj: pd.DataFrame):
        self._obj = pandas_obj

    def merge(self, right: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
        return lineage_merge(self._obj, right, *args, **kwargs)

    def join(self, right: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
        return lineage_join(self._obj, right, *args, **kwargs)

    def impute(self, **kwargs) -> pd.DataFrame:
        return update_table_data_lineage(self._obj, **kwargs)
