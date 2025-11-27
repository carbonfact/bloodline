import pandas as pd

import bloodline as bl
from bloodline import erd


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

    def test_join_on_single_key_tracks_lineage(self):
        """Test that joining two tables on a single key properly tracks data lineage."""
        lineage = bl.Lineage()

        # Create decorators for different sources
        database_source = lineage.with_source(
            source="DATABASE", metadata={"table": "customers", "file_path": "customers"}
        )
        api_source = lineage.with_source(source="API", metadata={"endpoint": "/orders", "file_path": "orders"})

        @database_source
        def load_customers() -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "customer_id": [1, 2, 3],
                    "name": ["Alice", "Bob", "Charlie"],
                    "city": ["NYC", "LA", "SF"],
                }
            )

        @api_source
        def load_orders() -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "customer_id": [1, 2, 2, 3],
                    "order_id": [101, 102, 103, 104],
                    "amount": [250.0, 150.0, 300.0, 75.0],
                }
            )

        @lineage
        def join_tables(customers: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
            return pd.merge(customers, orders, on="customer_id", how="inner")

        # Load tables separately with different sources
        customers = load_customers()
        orders = load_orders()

        # Perform the join
        result = join_tables(customers, orders)

        # Verify the join worked correctly
        assert len(result) == 4
        assert list(result.columns) == ["customer_id", "name", "city", "order_id", "amount", "data_lineage"]

        # Verify data lineage column exists
        assert "data_lineage" in result.columns

        # Check that lineage is tracked for all columns
        first_row_lineage = result.iloc[0]["data_lineage"]
        assert "customer_id" in first_row_lineage
        assert "name" in first_row_lineage
        assert "city" in first_row_lineage
        assert "order_id" in first_row_lineage
        assert "amount" in first_row_lineage

        # Verify that customer columns came from the DATABASE source
        assert first_row_lineage["name"]["source_type"] == "DATABASE"
        assert first_row_lineage["name"]["source_metadata"]["table"] == "customers"
        assert first_row_lineage["city"]["source_type"] == "DATABASE"

        # Verify that order columns came from the API source
        assert first_row_lineage["order_id"]["source_type"] == "API"
        assert first_row_lineage["order_id"]["source_metadata"]["endpoint"] == "/orders"
        assert first_row_lineage["amount"]["source_type"] == "API"

        # Verify the join key tracks lineage from one of the sources (either is valid)
        customer_id_lineage = first_row_lineage["customer_id"]
        assert customer_id_lineage["source_type"] in ["DATABASE", "API"]

        # Verify the relationship has been picked up
        assert len(lineage.erd.relationships) == 1
        relationship = list(lineage.erd.relationships)[0]
        assert relationship.left_name == "customers"
        assert relationship.left_key == "customer_id"
        assert relationship.right_name == "orders"
        assert relationship.right_key == "customer_id"
        assert relationship.relationship_type == erd.RelationshipType.ONE_TO_MANY
