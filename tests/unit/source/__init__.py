import pytest

import bloodline as bl


class TestSource:
    def test_source_creation_with_metadata(self):
        source = bl.Source(
            source_type=bl.get_source_type(name="DATA_SOURCE"),
            source_metadata={"path": "data/test.csv", "format": "csv"},
        )

        assert source.source_metadata["path"] == "data/test.csv"
        assert source.source_metadata["format"] == "csv"

    def test_source_creation_without_metadata(self):
        source = bl.Source(source_type=bl.get_source_type(name="DATA_SOURCE"))

        assert source.source_type is not None
        assert hasattr(source, "source_metadata")

    def test_rule_source_creation(self):
        source = bl.Source.rule(name="test_transformation")

        assert source is not None

    def test_get_source_type(self):
        """Test getting source types."""
        source_type = bl.get_source_type(name="DATA_SOURCE")
        assert source_type is not None

        rule_type = bl.get_source_type(name="RULE")
        assert rule_type is not None


class TestSourceTypes:
    def test_data_source_type(self):
        source_type = bl.get_source_type(name="DATA_SOURCE")
        assert source_type is not None

    def test_rule_source_type(self):
        source_type = bl.get_source_type(name="RULE")
        assert source_type is not None

    def test_invalid_source_type(self):
        with pytest.raises((ValueError, KeyError)):
            bl.get_source_type(name="INVALID_TYPE")
