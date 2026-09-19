"""
Tests for src/inspect_dataset.py module
"""

import json
from pathlib import Path
import pytest
from src.inspect_dataset import normalize_inbound_series, inspect_dataset, calculate_sha256
import pandas as pd


def test_normalize_inbound_series():
    """Verify explicit inbound normalization logic without using bool()."""
    s_bool = pd.Series([True, False, True])
    pd.testing.assert_series_equal(normalize_inbound_series(s_bool), s_bool)

    s_str = pd.Series(["True", "False", "1", "0", "t", "f"])
    expected = pd.Series([True, False, True, False, True, False])
    pd.testing.assert_series_equal(normalize_inbound_series(s_str), expected)

    s_invalid = pd.Series(["invalid_flag"])
    with pytest.raises(ValueError, match="Unexpected non-boolean value"):
        normalize_inbound_series(s_invalid)


def test_calculate_sha256(tmp_path: Path):
    """Verify SHA256 computation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")
    # sha256 of 'hello world' is b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    digest = calculate_sha256(test_file)
    assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_inspect_dataset_file_not_found(tmp_path: Path):
    """Verify FileNotFoundError when input CSV is missing."""
    missing_csv = tmp_path / "nonexistent.csv"
    with pytest.raises(FileNotFoundError, match="Dataset file not found"):
        inspect_dataset(csv_path=missing_csv)
