import pandas as pd
import pytest

import bloodline as bl


class TestIntegration:
    def test_complete_workflow(self):
        initial_source = bl.Source(
            source_type=bl.get_source_type(name="DATA_SOURCE"), source_metadata={"path": "input/data.csv"}
        )

        df = bl.update_table_data_lineage(
            table=pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]}), default_source=initial_source
        )

        @bl.update_data_lineage()
        def process_data(df: pd.DataFrame) -> pd.DataFrame:
            df["doubled"] = df["value"] * 2
            df["category"] = df["value"].apply(lambda x: "high" if x > 15 else "low")
            return df

        df = process_data(df)

        lookup_df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        lookup_df = bl.update_table_data_lineage(lookup_df)

        result = df.lineage.merge(lookup_df, on="id", how="left")

        result["final_score"] = result["doubled"] + result["id"]
        result.lineage.impute(default_source=bl.Source.rule(name="final_calculation"))

        assert "data_lineage" in result.columns
        assert "doubled" in result.columns
        assert "category" in result.columns
        assert "name" in result.columns
        assert "final_score" in result.columns
        assert len(result) == 3

    def test_multiple_transformations_chain(self):
        source = bl.Source(source_type=bl.get_source_type(name="DATA_SOURCE"), source_metadata={"path": "test.csv"})

        df = bl.update_table_data_lineage(
            table=pd.DataFrame({"x": [1, 2, 3, 4], "y": [5, 6, 7, 8]}), default_source=source
        )

        @bl.update_data_lineage()
        def step1(df: pd.DataFrame) -> pd.DataFrame:
            df["sum"] = df["x"] + df["y"]
            return df

        @bl.update_data_lineage()
        def step2(df: pd.DataFrame) -> pd.DataFrame:
            df["product"] = df["x"] * df["y"]
            return df

        @bl.update_data_lineage()
        def step3(df: pd.DataFrame) -> pd.DataFrame:
            df["ratio"] = df["sum"] / df["product"]
            return df.dropna()

        result = step3(step2(step1(df)))

        assert "data_lineage" in result.columns
        assert all(col in result.columns for col in ["x", "y", "sum", "product", "ratio"])

    def test_error_handling_in_workflow(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        @bl.update_data_lineage()
        def division(df: pd.DataFrame) -> pd.DataFrame:
            df["result"] = df["a"] / df["b"]
            return df

        result = division(df)
        assert "result" in result.columns

    def test_lineage_data_export(self, lineage_dataframe):
        lineage_dataframe["computed"] = lineage_dataframe["a"] * 2
        lineage_dataframe.lineage.impute()

        lineage_dict = lineage_dataframe["data_lineage"].to_dict()

        assert isinstance(lineage_dict, dict)
        assert len(lineage_dict) == len(lineage_dataframe)
