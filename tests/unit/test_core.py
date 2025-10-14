import pandas as pd
import pytest

import bloodline as bl


class TestDataLineage:
    def test_update_table_data_lineage(self, sample_dataframe, data_source):
        df_with_lineage = bl.update_table_data_lineage(table=sample_dataframe, default_source=data_source)

        assert "data_lineage" in df_with_lineage.columns
        assert len(df_with_lineage) == len(sample_dataframe)
        assert all(col in df_with_lineage.columns for col in sample_dataframe.columns)

    def test_update_table_data_lineage_without_source(self, sample_dataframe):
        df_with_lineage = bl.update_table_data_lineage(table=sample_dataframe)

        assert "data_lineage" in df_with_lineage.columns
        assert len(df_with_lineage) == len(sample_dataframe)

    def test_lineage_preservation_after_operations(self, lineage_dataframe):
        filtered_df = lineage_dataframe[lineage_dataframe["a"] > 15]
        assert "data_lineage" in filtered_df.columns

        # Test column addition
        lineage_dataframe["new_col"] = lineage_dataframe["a"] * 2
        assert "data_lineage" in lineage_dataframe.columns

    def test_lineage_data_structure(self, lineage_dataframe):
        """Test the structure of lineage data."""
        lineage_dict = lineage_dataframe["data_lineage"].iloc[0]

        assert isinstance(lineage_dict, (dict, str)) or hasattr(lineage_dict, "__dict__")


class TestDataLineageDecorator:
    def test_decorator_basic_functionality(self, lineage_dataframe):
        @bl.update_data_lineage()
        def multiply_column(df: pd.DataFrame) -> pd.DataFrame:
            df["c"] = df["a"] * 2
            return df

        result = multiply_column(lineage_dataframe.copy())

        assert "c" in result.columns
        assert "data_lineage" in result.columns 
        assert all(result["c"] == result["a"] * 2)

    def test_decorator_with_multiple_operations(self, lineage_dataframe):
        @bl.update_data_lineage()
        def complex_transformation(df: pd.DataFrame) -> pd.DataFrame:
            df["sum_col"] = df["a"] + df["b"]
            df["ratio"] = df["a"] / df["b"]
            df = df[df["a"] > 10]
            return df

        result = complex_transformation(lineage_dataframe.copy())

        assert "sum_col" in result.columns
        assert "ratio" in result.columns
        assert "data_lineage" in result.columns
        assert len(result) <= len(lineage_dataframe)
