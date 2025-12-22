import pandas as pd

from bloodline.apply import apply_data_lineage
from bloodline.source import Source, SourceType
from bloodline.tracking import disable_data_lineage_tracking, enable_data_lineage_tracking


def build_df() -> pd.DataFrame:
    df = pd.DataFrame({"id": [1, 2], "value": [None, 42]})
    df["data_lineage"] = [
        {"id": Source(source_type=SourceType.DATA_SOURCE, source_metadata={"path": "foo"}).to_dict()},
        {},
    ]
    return df


def test_apply_sets_default_source_when_missing():
    df = build_df()
    updated = apply_data_lineage(
        df, default_source=Source(source_type=SourceType.UNKNOWN, source_metadata={"origin": "test"})
    )
    assert updated.loc[1, "data_lineage"]["value"]["source_metadata"] == {"origin": "test"}


def test_inheritance_copies_parent_lineage():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "parent": [10, 20],
            "child": [11, 21],
            "data_lineage": [
                {"parent": Source(source_type=SourceType.DATA_SOURCE, source_metadata={"path": "a"}).to_dict()},
                {"parent": Source(source_type=SourceType.DATA_SOURCE, source_metadata={"path": "b"}).to_dict()},
            ],
        }
    )
    updated = apply_data_lineage(
        df,
        default_source=None,
        inheritance={"child": "parent"},
    )
    assert updated.loc[0, "data_lineage"]["child"] == updated.loc[0, "data_lineage"]["parent"]


def test_disabled_tracking_initializes_empty_dicts():
    df = pd.DataFrame({"id": [1, 2]})
    disable_data_lineage_tracking()
    try:
        updated = apply_data_lineage(df, default_source=Source(source_type=SourceType.UNKNOWN, source_metadata={}))
        assert "data_lineage" not in updated.columns
    finally:
        enable_data_lineage_tracking()


def test_override_replaces_existing_lineage():
    df = pd.DataFrame(
        {
            "id": [1],
            "value": [100],
            "data_lineage": [
                {"value": Source(source_type=SourceType.DATA_SOURCE, source_metadata={"path": "a"}).to_dict()}
            ],
        }
    )
    updated = apply_data_lineage(
        df,
        default_source=Source(source_type=SourceType.UNKNOWN, source_metadata={"reason": "override"}),
        column_names=["value"],
        override=True,
    )
    assert updated.loc[0, "data_lineage"]["value"]["source_metadata"] == {"reason": "override"}
