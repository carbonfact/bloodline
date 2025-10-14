import pandas as pd
import pytest

import bloodline as bl


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({"id": [1, 2, 3], "a": [10, 20, 30], "b": [100, 200, 300]})


@pytest.fixture
def data_source():
    return bl.Source(
        source_type=bl.get_source_type(name="DATA_SOURCE"), source_metadata={"path": "test/data.csv", "format": "csv"}
    )


@pytest.fixture
def rule_source():
    return bl.Source.rule(name="test_rule")


@pytest.fixture
def lineage_dataframe(sample_dataframe, data_source):
    return bl.update_table_data_lineage(sample_dataframe, default_source=data_source)
