"""Runtime switch to enable/disable data lineage instrumentation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

__all__ = [
    "is_data_lineage_tracked",
    "enable_data_lineage_tracking",
    "disable_data_lineage_tracking",
    "temporarily_disable_tracking",
]

_TRACKING_ENABLED = True


def is_data_lineage_tracked() -> bool:
    return _TRACKING_ENABLED


def _set_data_lineage_tracking(enabled: bool) -> None:
    global _TRACKING_ENABLED
    _TRACKING_ENABLED = bool(enabled)


def enable_data_lineage_tracking() -> None:
    _set_data_lineage_tracking(True)


def disable_data_lineage_tracking() -> None:
    _set_data_lineage_tracking(False)


@contextmanager
def temporarily_disable_tracking() -> Iterator[None]:
    previous = is_data_lineage_tracked()
    try:
        _set_data_lineage_tracking(False)
        yield
    finally:
        _set_data_lineage_tracking(previous)
