# 𐌱𐌻𐍉𐍉𐌳𐌻𐌹𐌽𐌴

#![alt text](image.png)

[![PyPI](https://img.shields.io/pypi/v/bloodline.svg)](https://pypi.org/project/bloodline/)
[![Testing](https://github.com/carbonfact/bloodline/actions/workflows/test.yml/badge.svg)](https://github.com/carbonfact/bloodline/actions/workflows/test.yml)

Bloodline is a tiny helper library that lets you track *row-level* provenance for pandas dataframes without rewriting your business logic. Decorate a function, keep calling `pd.read_csv` / `pd.merge` / `pd.DataFrame.join` as usual, and Bloodline injects a `data_lineage` column that records—per row and per column—where values came from.

## Install

```sh
pip install bloodline
```

For local development:

```sh
git clone https://github.com/carbonfact/bloodline
uv sync
uv run pytest
```

## Getting started

```python
import pandas as pd
import bloodline as bl

lineage = bl.Lineage(
    default_source=bl.Source.hard_coded(reason="default"),
    extra_sources_type=("HEURISTIC", "RULE"),
)

@lineage
def enrich_products(products_path, suppliers_path):
    products = pd.read_csv(products_path)
    suppliers = pd.read_csv(suppliers_path)
    merged = pd.merge(products, suppliers, on="product_id", how="left")
    return merged


result = enrich_products("products.csv", "suppliers.csv")
print(result["data_lineage"].iloc[0])
```

What happens under the hood:

1. `@lineage` enters a context manager, installing lineage-aware pandas hooks.
2. `pd.read_csv` records `{"source_type": "DATA_SOURCE", "source_metadata": {"file_path": ...}}` automatically.
3. `pd.merge` (and `DataFrame.join`) fuse any existing `data_lineage` columns, so you never end up with `_x/_y` suffixes.
4. When the function returns, Bloodline imputes lineage for any new columns using the decorator’s default source.

> ⚠️ If the wrapped function doesn’t return a single dataframe, Bloodline logs a warning (via `loguru`) and skips lineage updates.

## Key concepts

- **Source types** – the OSS build ships two canonical types: `SourceType.DATA_SOURCE` (data you read) and `SourceType.HARD_CODED` (values you derive). You can still create ad-hoc string-based sources via `Lineage.with_source`.
- **`data_lineage` column** – every dataframe touched by Bloodline carries a dict per row: `{column_name: {"source_type": ..., "source_metadata": {...}}}`.
- **Scoped pandas hooks** – Bloodline temporarily patches `pd.read_csv`, `pd.read_excel`, `pd.merge`, and `DataFrame.join` while a decorated function executes. Outside that scope, pandas behaves exactly as normal. This part is probably what brings the most value.

### Why context-scoped hooks?

We tried dataframe accessors and global monkeypatches. We want something better, that could work without updating your current code but still give you control

Context-scoped hooks hit the sweet spot:

1. Hooks exist only while a decorated function runs, so pandas behaves normally everywhere else.
2. IO helpers automatically tag provenance (file paths for `pd.read_csv` and `pd.read_excel`) without asking users to do anything special.
3. Nested decorators cooperate because each scope manages its own patches; the innermost decorator always sets the active default source.

If you need Bloodline to disappear altogether, call `disable_data_lineage_tracking()`.

## Manual adjustments

Because we do not cover all pandas operations yet, we enable manual adjustments. Here’s an example of our product-mass rule we use at Carbonfact: only the selected SKUs change, and we force their lineage to `HEURISTIC` while leaving the rest untouched.

```python
from bloodline.apply import apply_data_lineage
from bloodline.source import Source

mask = df["sku"].isin(selected_skus)
df.loc[mask, "sku_mass"] = override_value

df = apply_data_lineage(
    table=df,
    default_source=Source(source_type="HEURISTIC", source_metadata={"heuristic_name": "mass_filler"}),
    row_mask=mask,
    column_names=["sku_mass"],
    override=True,
)
```

> ℹ️ Add `inheritance={"child_column": "parent_column"}` when calculating derived columns and Bloodline will copy the parent’s lineage automatically. Empty cells are ignored so the `data_lineage` dict stays lean.

## Toggling tracking

Bloodline exposes `is_data_lineage_tracked()`, `enable_data_lineage_tracking()`, `disable_data_lineage_tracking()`, and `temporarily_disable_tracking()` (context manager) under `bloodline.tracking`. Use these around bulk operations where provenance isn’t needed.

## Design recap

- Users write normal pandas code. They shouldn’t swap `pd.merge` for a custom accessor.
- The `Lineage` decorator installs temporary hooks on pandas APIs (currently `read_csv`, `read_excel`, `merge`, `DataFrame.join`). Hooks must be context-scoped so that `pd` behaves normally elsewhere.
- Returning from the decorator triggers a final `apply_data_lineage` pass, which fills any gaps column-by-column.

## Next steps

- Bring more pandas operations under the hook manager (prime candidates: `fillna`, `where`, `DataFrame.assign`).
- Flesh out the developer guide with real-world recipes as new hooks land.
- Experiment with lightweight lineage visualizations once the API surface settles.
