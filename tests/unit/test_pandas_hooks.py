import pandas as pd

from bloodline.constants import DATA_LINEAGE_COLUMN
from bloodline.pandas_hooks import pandas_lineage_patched


def test_read_csv_tags_data_source(tmp_path):
    csv_path = tmp_path / "data.csv"
    rows = [
        {"id": 1, "value": 10},
        {"id": 2, "value": 20},
    ]
    csv_path.write_text("id,value\n", encoding="utf-8")
    with csv_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(f"{row['id']},{row['value']}\n")

    with pandas_lineage_patched():
        df = pd.read_csv(csv_path)

    assert DATA_LINEAGE_COLUMN in df.columns
    assert df.loc[0, DATA_LINEAGE_COLUMN]["id"]["source_type"] == "DATA_SOURCE"


def test_merge_fuses_lineage_columns(tmp_path):
    left = pd.DataFrame(
        {
            "id": [1],
            "value": [10],
            DATA_LINEAGE_COLUMN: [
                {
                    "id": {"source_type": "DATA_SOURCE"},
                    "value": {"source_type": "DATA_SOURCE"},
                }
            ],
        }
    )
    right = pd.DataFrame(
        {
            "id": [1],
            "extra": [99],
            DATA_LINEAGE_COLUMN: [{"extra": {"source_type": "HARD_CODED"}}],
        }
    )

    with pandas_lineage_patched():
        merged = pd.merge(left, right, on="id")

    assert set(merged.columns) == {"id", "value", "extra", DATA_LINEAGE_COLUMN}
    assert "extra" in merged.loc[0, DATA_LINEAGE_COLUMN]
