# Bloodline

![alt text](image.png)

![PyPI version](https://img.shields.io/pypi/v/bloodline.svg)
[![Documentation Status](https://readthedocs.org/projects/bloodline/badge/?version=latest)](https://bloodline.readthedocs.io/en/latest/?version=latest)

Bloodline is a minimal python package used for row-level data lineage tracking in pandas dataframes (only for now). Bloodline helps Carbonfact track data transformations and their associated metadata through a data pipeline.

> **Why create bloodline?**
>
> - most lineage tools cover only table and column level lineage
> - we need row-level transparency for our carbon footprint calculations
> - it is a way to track customers' data quality

## Installation

You can install Bloodline via pip:

```bash
pip install bloodline
```

### Development installation

To install Bloodline for development, clone the repository and install the package using `uv`:

```bash
uv sync
```

To run tets, use:

```bash
uv run pytest
```

## Usage

### Tracking data lineage

You have two options to track data lineage:

1. Use the `@update_data_lineage` decorator to automatically track lineage when applying functions to dataframes.

```python
import pandas as pd
import bloodline as bl

@bl.update_data_lineage()
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    # Your data transformation logic here
    return df

# Example usage
data = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6]
})
data = transform_data(data)
```

2. Using the `update_table_data_lineage` function to manually update lineage after transformations.

```python
import pandas as pd
import bloodline as bl

initial_data_source = bl.Source(
    source_type=bl.get_source_type(name="DATA_SOURCE"),
    source_metadata={"path": "input/data.csv"},
)

df = bl.update_table_data_lineage(
    table=pd.DataFrame({"id": [1, 2], "a": [10, 20]}),
    default_source=initial_data_source,
)
```

### Adding new sources

At Carbonfact, we have a list of predefined source types. But you can add new sources as follows:

```python
import bloodline as bl

new_source = bl.register_source_type("MY_NEW_SOURCE")
```

And even overrid the default source registry:

```python
import bloodline as bl

bl.set_source_registry(
    initial=("MY_NEW_SOURCE", "ANOTHER_SOURCE")
)
```

## Limitations

WIP
