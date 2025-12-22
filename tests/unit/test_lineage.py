import logging

import pandas as pd

from bloodline.constants import DATA_LINEAGE_COLUMN
from bloodline.lineage import Lineage
from bloodline.source import SourceType


def test_lineage_adds_column_with_default_source():
    lineage = Lineage()

    @lineage
    def build_df():
        return pd.DataFrame({"value": [1, 2]})

    result = build_df()
    assert DATA_LINEAGE_COLUMN in result.columns
    assert result.loc[0, DATA_LINEAGE_COLUMN]["value"]["source_type"] == SourceType.UNKNOWN.value


def test_with_source_allows_custom_type():
    lineage = Lineage()
    heuristic = lineage.with_source(source="HEURISTIC", metadata={"heuristic_name": "mass_filler"})

    @heuristic
    def fill(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["mass"] = 2
        return df

    result = fill(pd.DataFrame({"mass": [0]}))
    assert result.loc[0, DATA_LINEAGE_COLUMN]["mass"]["source_type"] == "HEURISTIC"
    assert result.loc[0, DATA_LINEAGE_COLUMN]["mass"]["source_metadata"]["heuristic_name"] == "mass_filler"


def test_non_dataframe_result_emits_warning(caplog):
    lineage = Lineage()

    @lineage
    def invalid():
        return "oops"

    with caplog.at_level(logging.WARNING):
        assert invalid() == "oops"

    assert any("Lineage decorator expected" in record.message for record in caplog.records)


def test_tuple_return():
    lineage = Lineage()

    @lineage(return_arg=0)
    def build_df():
        return pd.DataFrame({"value": [1, 2]}), "foo"

    table, _ = build_df()
    assert DATA_LINEAGE_COLUMN in table.columns
    assert table.loc[0, DATA_LINEAGE_COLUMN]["value"]["source_type"] == SourceType.UNKNOWN.value


def test_dict_return():
    lineage = Lineage()

    @lineage(return_arg="table")
    def build_df():
        return {"table": pd.DataFrame({"value": [1, 2]}), "foo": "bar"}

    table = build_df()["table"]
    assert DATA_LINEAGE_COLUMN in table.columns
    assert table.loc[0, DATA_LINEAGE_COLUMN]["value"]["source_type"] == SourceType.UNKNOWN.value


def test_tuple_return_with_source():
    lineage = Lineage()
    heuristic = lineage.with_source(source="HEURISTIC", metadata={"heuristic_name": "mass_filler"})

    @heuristic(return_arg=0)
    def fill(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        df = df.copy()
        df["mass"] = 2
        return df, "foo"

    table, _ = fill(pd.DataFrame({"mass": [0]}))
    assert table.loc[0, DATA_LINEAGE_COLUMN]["mass"]["source_type"] == "HEURISTIC"
    assert table.loc[0, DATA_LINEAGE_COLUMN]["mass"]["source_metadata"]["heuristic_name"] == "mass_filler"
