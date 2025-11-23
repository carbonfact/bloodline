"""
Test module for README.md doctests.

This module enables pytest to discover and run doctests in README.md.
"""

import doctest
import pathlib


def test_readme_doctests():
    """Run doctests from README.md."""
    readme_path = pathlib.Path(__file__).parent.parent / "README.md"
    result = doctest.testfile(
        str(readme_path),
        module_relative=False,
        optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE,
    )
    assert result.failed == 0, f"{result.failed} doctest(s) failed in README.md"
