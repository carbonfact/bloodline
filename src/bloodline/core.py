import typing

import pandas as pd

from .constants import DATA_LINEAGE_COLUMN
from .source import DataLineage, Source
from .source.registry import get_source_registry
from .utils import is_empty

__all__ = ["register_source_type", "update_data_lineage", "update_table_data_lineage"]

DEFAULT_SOURCE = Source(source_type=get_source_registry().get("HARD_CODING"), source_metadata={})


def register_source_type(name: str):
    """Public helper to register or get a custom SourceType by name."""
    return get_source_registry().register(name)


def get_source_type(name: str):
    """Public helper to register or get a custom SourceType by name."""
    return get_source_registry().get(name)


def update_data_lineage(
    default_source: Source = DEFAULT_SOURCE,
    inheritance: dict[str, str] | None = None,
) -> typing.Callable:
    """
    This is a decorator.

    Shaping usually involves loading data from a data source. When the data source is loaded, a
    data_lineage column is added to the dataframe. This columns contains a dictionary that maps
    each data point to its data source. There are two cases where this might not be the case:

    1. The shaping didn't involve loading data from a data source. In this case, each data point
        can be considered to be hard coded.
    2. The shaping loaded data from a data source, but then did some extra processing on it and
        added extra columns. The data lineage for these columns needs to be imputed.

    Parameters
    ----------
    inheritance
        Optionally indicates where each new column comes from in the existing dataframe. The
        dictionary should be in the format {new_column: existing_column}.
    default_source
        The default source to set for fields that do not yet have a data lineage.
    """

    def decorator(func: typing.Callable[..., pd.DataFrame]) -> typing.Callable[..., pd.DataFrame]:
        def wrapper(*args, **kwargs) -> pd.DataFrame:
            table = func(*args, **kwargs)
            return update_table_data_lineage(table=table, default_source=default_source, inheritance=inheritance)

        return wrapper

    return decorator


def update_table_data_lineage(
    table: pd.DataFrame,
    default_source: Source | None = None,
    inheritance: dict[str, str] | None = None,
    row_mask: pd.Series | None = None,
    column_names: list[str] | None = None,
    override: bool = False,
) -> pd.DataFrame:
    """
    In most cases the update_data_lineage decorator should be sufficient to handle data lineage.
    But in some cases, there is a need for fine-grained control. This is particularly true in the
    case of rules, where the existing data lineage needs to be overriden.

    Parameters
    ----------
    table
        The table to update. This should be a dataframe with a data_lineage column.
    default_source
        The default source to set for fields that do not yet have a data lineage.
    inheritance
        Optionally indicates where each new column comes from in the existing dataframe. The
        dictionary should be in the format {new_column: existing_column}.
    row_mask
        Optionally indicates which rows to update. This should be a boolean series with the same
        length as the dataframe.
    column_names
        Optionally indicates which columns to update. This should be a list of column names. All
        columns are considered by default. The only benefit of using this is to speed up the
        function, as it will only iterate over the columns that are specified.
    override
        If True, the default_source will be set for all columns, even if they already have a
        data lineage. If False, the default_source will only be set for columns that do not have a
        data lineage.
    """
    inheritance = inheritance or {}
    table_slice = table.loc[row_mask] if row_mask is not None else table
    columns_to_update = (
        (set(column_names) & set(table_slice.columns)) if column_names is not None else set(table_slice.columns)
    )

    default_source_dict = default_source.to_dict() if isinstance(default_source, Source) else default_source

    # Prepare existing lineage column or create empty dicts
    if DATA_LINEAGE_COLUMN not in table_slice.columns:
        table_slice = table_slice.copy()
        table_slice[DATA_LINEAGE_COLUMN] = [{} for _ in range(len(table_slice))]

    imputed = []
    for _, row in table_slice.iterrows():
        dl: DataLineage = row.get(DATA_LINEAGE_COLUMN, {})
        dl = dict(dl) if isinstance(dl, dict) else {}  # copy, handle NaN

        # Clean empties
        dl = {k: v for k, v in dl.items() if v is not None}

        # New columns to set lineage on
        new_columns = (
            columns_to_update
            - (set(dl.keys()) if not override else set())
            - {DATA_LINEAGE_COLUMN, "input_payload"}  # keep your exclusion
        )
        for col in new_columns:
            if col not in row or is_empty(row[col]):
                continue
            parent = inheritance.get(col)
            if parent and parent in dl and not override:
                dl[col] = dl[parent]  # inherit parent's source dict
            elif default_source_dict:
                dl[col] = default_source_dict

        # Drop lineage entries for columns that disappeared or became empty
        for k in list(dl.keys()):
            if k not in row or is_empty(row[k]):
                del dl[k]

        imputed.append(dl)

    imputed_series = pd.Series(imputed, index=table_slice.index)

    if row_mask is not None:
        table.loc[row_mask, DATA_LINEAGE_COLUMN] = imputed_series
    else:
        table.loc[:, DATA_LINEAGE_COLUMN] = imputed_series
    return table
