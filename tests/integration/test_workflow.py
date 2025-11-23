import pandas as pd

import bloodline as bl


class TestIntegrationWorkflow:
    def test_lineage_flow_with_rule_override(self):
        lineage = bl.Lineage(
            default_source=bl.Source.unknown(reason="default"),
            extra_sources_type=("HEURISTIC", "RULE"),
        )

        @lineage
        def enrich(products: pd.DataFrame, suppliers: pd.DataFrame) -> pd.DataFrame:
            merged = pd.merge(products, suppliers, on="sku", how="left")
            merged["mass_in_grams"] = merged["mass"]
            return merged

        heuristic = lineage.with_source(source="HEURISTIC", metadata={"heuristic_name": "fallback_fill"})

        @heuristic
        def fill_missing(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()
            mask = df["mass_in_grams"].isna()
            df.loc[mask, "mass_in_grams"] = df.loc[mask, "fallback_mass"]
            return df

        products = pd.DataFrame(
            {
                "sku": ["SKU-001", "SKU-002", "SKU-003"],
                "mass": [150, None, None],
                "price": [20, 25, 30],
            }
        )
        suppliers = pd.DataFrame(
            {
                "sku": ["SKU-001", "SKU-002", "SKU-003"],
                "fallback_mass": [150, 180, 210],
            }
        )

        enriched = fill_missing(enrich(products, suppliers))
        assert "data_lineage" in enriched.columns

        heuristic_entry = enriched.loc[enriched["sku"] == "SKU-003", "data_lineage"].iloc[0]["mass_in_grams"]
        assert heuristic_entry["source_type"] == "HEURISTIC"
        assert heuristic_entry["source_metadata"]["heuristic_name"] == "fallback_fill"

        mask = enriched["sku"] == "SKU-002"
        enriched.loc[mask, "mass_in_grams"] = 250
        rule_source = bl.Source(source_type="RULE", source_metadata={"rule_id": "mass_override"})
        enriched = bl.apply_data_lineage(
            table=enriched,
            default_source=rule_source,
            row_mask=mask,
            column_names=["mass_in_grams"],
            override=True,
        )

        rule_entry = enriched.loc[mask, "data_lineage"].iloc[0]["mass_in_grams"]
        assert rule_entry["source_type"] == "RULE"
        assert rule_entry["source_metadata"]["rule_id"] == "mass_override"

    def test_decorator_reads_csv_and_preserves_metadata(self, tmp_path):
        csv_path = tmp_path / "products.csv"
        csv_path.write_text("sku,mass\nSKU-001,100\n", encoding="utf-8")

        lineage = bl.Lineage()

        @lineage
        def load_products() -> pd.DataFrame:
            return pd.read_csv(csv_path)

        df = load_products()
        lineage_entry = df.loc[0, "data_lineage"]["sku"]
        assert lineage_entry["source_type"] == bl.SourceType.DATA_SOURCE.value
        assert str(csv_path) in lineage_entry["source_metadata"]["file_path"]
