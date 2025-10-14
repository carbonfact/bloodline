import pytest

import bloodline as bl
from bloodline.source.registry import SourceRegistry, SourceType


class TestSourceTypes:
    def test_data_source_type(self):
        source_type = bl.get_source_type(name="DATA_SOURCE")
        assert source_type is not None
        assert source_type.name == "DATA_SOURCE"

    def test_rule_source_type(self):
        source_type = bl.get_source_type(name="RULE")
        assert source_type is not None
        assert source_type.name == "RULE"

    def test_all_default_source_types(self):
        expected_types = ["DATA_SOURCE", "HEURISTIC", "RULE", "HARD_CODING", "DATA_EXCHANGE"]

        for source_name in expected_types:
            source_type = bl.get_source_type(name=source_name)
            assert source_type is not None
            assert source_type.name == source_name

    def test_invalid_source_type(self):
        with pytest.raises((ValueError, KeyError)):
            bl.get_source_type(name="INVALID_TYPE")

    def test_get_source_type_consistency(self):
        # Getting the same source type multiple times should return the same object
        source1 = bl.get_source_type(name="DATA_SOURCE")
        source2 = bl.get_source_type(name="DATA_SOURCE")

        assert source1 is source2


class TestSourceRegistry:
    def test_empty_registry_creation(self):
        registry = SourceRegistry()
        assert len(registry.sources) == 0

    def test_registry_with_initial_sources(self):
        registry = SourceRegistry(initial=["SOURCE1", "SOURCE2"])
        assert len(registry.sources) == 2
        assert any(s.name == "SOURCE1" for s in registry.sources)
        assert any(s.name == "SOURCE2" for s in registry.sources)

    def test_register_new_source(self):
        registry = SourceRegistry()
        source = registry.register("NEW_SOURCE")

        assert isinstance(source, SourceType)
        assert source.name == "NEW_SOURCE"
        assert len(registry.sources) == 1
        assert registry.sources[0] == source

    def test_register_duplicate_source(self):
        registry = SourceRegistry(initial=["EXISTING_SOURCE"])

        with pytest.raises(ValueError, match="Source 'EXISTING_SOURCE' is already registered"):
            registry.register("EXISTING_SOURCE")

    def test_get_existing_source(self):
        registry = SourceRegistry(initial=["TEST_SOURCE"])
        source = registry.get("TEST_SOURCE")

        assert isinstance(source, SourceType)
        assert source.name == "TEST_SOURCE"

    def test_get_nonexistent_source(self):
        registry = SourceRegistry()

        with pytest.raises(KeyError, match="Source 'NONEXISTENT' is not registered"):
            registry.get("NONEXISTENT")

    def test_sources_property_returns_copy(self):
        registry = SourceRegistry(initial=["SOURCE1"])
        sources_list = registry.sources

        # Modifying the returned list shouldn't affect the registry
        sources_list.clear()
        assert len(registry.sources) == 1


class TestGlobalSourceRegistryFunctions:
    def test_get_source_registry(self):
        registry = bl.source.registry.get_source_registry()
        assert isinstance(registry, SourceRegistry)
        assert len(registry.sources) > 0

    def test_default_sources_exist(self):
        registry = bl.source.registry.get_source_registry()
        source_names = [s.name for s in registry.sources]

        expected_defaults = ["DATA_SOURCE", "HEURISTIC", "RULE", "HARD_CODING", "DATA_EXCHANGE"]
        for expected in expected_defaults:
            assert expected in source_names

    def test_set_source_registry(self):
        # Save original registry
        original_registry = bl.source.registry.get_source_registry()

        try:
            # Create and set new registry
            new_registry = SourceRegistry(initial=["CUSTOM_SOURCE"])
            bl.source.registry.set_source_registry(new_registry)

            # Verify the registry was changed
            current_registry = bl.source.registry.get_source_registry()
            assert current_registry is new_registry
            assert len(current_registry.sources) == 1
            assert current_registry.sources[0].name == "CUSTOM_SOURCE"

        finally:
            # Restore original registry
            bl.source.registry.set_source_registry(original_registry)

    def test_registry_persistence_across_calls(self):
        registry1 = bl.source.registry.get_source_registry()
        registry2 = bl.source.registry.get_source_registry()

        assert registry1 is registry2
