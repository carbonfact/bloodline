import numpy as np
import pandas as pd


def is_empty(x) -> bool:
    if isinstance(x, set | list | tuple | dict) and len(x) == 0:
        return True
    if isinstance(x, float):
        return np.isnan(x)
    return x is None or pd.isna(x)
