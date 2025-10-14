import pandas as pd
import pytest

import bloodline as bl


class TestPandasAccessor:
    def test_lineage_accessor_exists(self, lineage_dataframe):
        assert hasattr(lineage_dataframe, "lineage")

    def test_lineage_merge(self, data_source):
        left = pd.DataFrame({"id": [1, 2, 3], "a": [10, 20, 30]})
        right = pd.DataFrame({"id": [2, 3, 4], "b": [99, 199, 299]})

        left = bl.update_table_data_lineage(left, default_source=data_source)
        right = bl.update_table_data_lineage(right, default_source=data_source)

        result = left.lineage.merge(right, on="id", how="left")

        assert "data_lineage" in result.columns
        assert "a" in result.columns
        assert "b" in result.columns
        assert len(result) == len(left)

    def test_lineage_merge_different_join_types(self, data_source):
        left = pd.DataFrame({"id": [1, 2], "a": [10, 20]})
        right = pd.DataFrame({"id": [2, 3], "b": [99, 199]})

        left = bl.update_table_data_lineage(left, default_source=data_source)
        right = bl.update_table_data_lineage(right, default_source=data_source)

        # Test inner join
        inner_result = left.lineage.merge(right, on="id", how="inner")
        assert len(inner_result) == 1
        assert "data_lineage" in inner_result.columns

        # Test outer join
        outer_result = left.lineage.merge(right, on="id", how="outer")
        assert len(outer_result) == 3
        assert "data_lineage" in outer_result.columns

    def test_lineage_impute(self, lineage_dataframe, rule_source):
        """Test the lineage impute functionality."""
        # Create some missing lineage scenario
        df = lineage_dataframe.copy()
        df["new_column"] = df["a"] * 3

        # Impute lineage for new column
        df.lineage.impute(default_source=rule_source)

        assert "data_lineage" in df.columns

    def test_lineage_impute_without_source(self, lineage_dataframe):
        """Test lineage impute without explicit source."""
        df = lineage_dataframe.copy()
        df["calculated"] = df["a"] + df["b"]

        # Should not raise error
        df.lineage.impute()

        assert "data_lineage" in df.columns


class TestAccessorEdgeCases:
    """Test edge cases for the pandas accessor."""

    def test_accessor_on_dataframe_without_lineage(self):
        """Test accessor behavior on DataFrame without lineage."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        # Should still have accessor but handle gracefully
        assert hasattr(df, "lineage")

    def test_merge_with_missing_lineage_column(self, data_source):
        """Test merge when one DataFrame lacks lineage."""
        left = pd.DataFrame({"id": [1, 2], "a": [10, 20]})
        right = pd.DataFrame({"id": [2, 3], "b": [99, 199]})

        left = bl.update_table_data_lineage(left, default_source=data_source)
        # right has no lineage

        # Should handle gracefully
        result = left.lineage.merge(right, on="id", how="left")
        assert "a" in result.columns
        assert "b" in result.columns
