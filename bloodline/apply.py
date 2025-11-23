"""Table-level helper to (re)compute data lineage."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .constants import DATA_LINEAGE_COLUMN
from .source import Source
from .tracking import is_data_lineage_tracked
from .utils import ensure_lineage_column, is_empty

__all__ = ["apply_data_lineage"]


def apply_data_lineage(
    table: pd.DataFrame,
    *,
    default_source: Source | dict[str, Any] | None,
    inheritance: dict[str, str] | None = None,
    row_mask: pd.Series | None = None,
    column_names: list[str] | None = None,
    override: bool = False,
) -> pd.DataFrame:
    """Ensure every (row, column) ends up with a data lineage."""

    if not is_data_lineage_tracked():
        return table

    inheritance = dict(inheritance or {})
    table_slice = table.loc[row_mask] if row_mask is not None else table
    table_slice = ensure_lineage_column(table_slice)

    candidates = set(table_slice.columns)
    if column_names is not None:
        candidates &= set(column_names)
    candidates.discard(DATA_LINEAGE_COLUMN)

    if isinstance(default_source, Source):
        default_payload = default_source.to_dict()
    else:
        default_payload = default_source

    imputed = []
    for _, row in table_slice.iterrows():
        lineage = row.get(DATA_LINEAGE_COLUMN, {})
        lineage = lineage if isinstance(lineage, dict) else {}
        lineage = {k: v for k, v in lineage.items() if v is not None}

        new_columns = candidates.copy()
        if not override:
            new_columns -= lineage.keys()

        for column in new_columns:
            if column not in row or is_empty(row[column]):
                continue

            parent = inheritance.get(column)
            if parent and parent in lineage and not override:
                lineage[column] = lineage[parent]
            elif default_payload:
                lineage[column] = default_payload

        for existing in list(lineage.keys()):
            if existing not in row or is_empty(row[existing]):
                del lineage[existing]

        imputed.append(lineage)

    imputed_series = pd.Series(imputed, index=table_slice.index)
    if row_mask is not None:
        table.loc[row_mask, DATA_LINEAGE_COLUMN] = imputed_series
    else:
        table.loc[:, DATA_LINEAGE_COLUMN] = imputed_series

    return table
