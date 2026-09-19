"""
Phase 1 Data Exploration Script for TWCS Dataset

Inspects dataset/twcs/twcs.csv, computes summary statistics,
validates columns & data types, normalizes inbound flags safely,
computes top outbound authors and SHA256 checksum, saving results to results/data_profile.json.
"""

import sys
import json
import hashlib
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List
import pandas as pd

# Path resolution relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = REPO_ROOT / "dataset" / "twcs" / "twcs.csv"
OUTPUT_PROFILE_PATH = REPO_ROOT / "results" / "data_profile.json"

CHUNK_SIZE = 100_000
REQUIRED_COLUMNS = {
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
}


def calculate_sha256(filepath: Path) -> str:
    """Calculates the SHA256 checksum of a file in binary chunks."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(1_048_576), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def normalize_inbound_series(series: pd.Series) -> pd.Series:
    """
    Normalizes 'inbound' column explicitly to boolean values without using bool() on strings.
    Handles booleans, string representations ('True', 'False', '1', '0'), and numerics safely.
    """
    if series.dtype == bool:
        return series

    # Convert to clean lowercase string for string/numeric inputs
    clean_series = series.astype(str).str.strip().str.lower()
    
    is_true = clean_series.isin({"true", "1", "1.0", "t", "yes"})
    is_false = clean_series.isin({"false", "0", "0.0", "f", "no"})
    
    # Identify invalid/unexpected values
    invalid_mask = ~(is_true | is_false | series.isna())
    if invalid_mask.any():
        invalid_sample = series[invalid_mask].iloc[0]
        raise ValueError(
            f"Unexpected non-boolean value found in 'inbound' column: {invalid_sample!r}. "
            "Expected boolean or boolean string ('True'/'False', '1'/'0')."
        )
        
    return is_true


def inspect_dataset(csv_path: Path = DEFAULT_DATASET_PATH, profile_output_path: Path = OUTPUT_PROFILE_PATH) -> Dict[str, Any]:
    """
    Reads the TWCS dataset in chunks, calculates summary metrics, top outbound authors,
    and SHA256 checksum, saving the result to a JSON profile.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found at: '{csv_path}'. "
            "Please ensure dataset/twcs/twcs.csv exists relative to repository root."
        )

    print(f"Calculating SHA256 checksum for {csv_path.name}...", flush=True)
    sha256_sum = calculate_sha256(csv_path)
    print(f"SHA256: {sha256_sum}", flush=True)

    total_rows = 0
    inbound_count = 0
    outbound_count = 0
    missing_counts: Counter = Counter()
    outbound_authors_counter: Counter = Counter()
    column_names: List[str] = []

    dtype_spec = {
        "tweet_id": str,
        "author_id": str,
        "response_tweet_id": str,
        "in_response_to_tweet_id": str,
        "created_at": str,
        "text": str,
    }

    print(f"Reading dataset in chunks of {CHUNK_SIZE:,} rows...", flush=True)
    
    try:
        reader = pd.read_csv(csv_path, chunksize=CHUNK_SIZE, dtype=dtype_spec)
        
        for i, chunk in enumerate(reader):
            if i == 0:
                column_names = list(chunk.columns)
                missing_cols = REQUIRED_COLUMNS - set(column_names)
                if missing_cols:
                    raise ValueError(
                        f"Dataset is missing required columns: {sorted(list(missing_cols))}. "
                        f"Found columns: {column_names}"
                    )

            # Update row count
            total_rows += len(chunk)

            # Track missing values per column
            for col in column_names:
                missing_counts[col] += int(chunk[col].isna().sum())

            # Explicitly normalize inbound values
            inbound_bool = normalize_inbound_series(chunk["inbound"])

            chunk_inbound_mask = inbound_bool.to_numpy()
            chunk_inbound_cnt = int(chunk_inbound_mask.sum())
            chunk_outbound_cnt = len(chunk) - chunk_inbound_cnt

            inbound_count += chunk_inbound_cnt
            outbound_count += chunk_outbound_cnt

            # Aggregate outbound author counts
            outbound_chunk = chunk[~chunk_inbound_mask]
            if not outbound_chunk.empty:
                outbound_authors_counter.update(outbound_chunk["author_id"].dropna())

            if (i + 1) % 5 == 0 or len(chunk) < CHUNK_SIZE:
                print(f"  Processed {total_rows:,} rows...", flush=True)

    except pd.errors.EmptyDataError:
        raise ValueError(f"The CSV file at '{csv_path}' is empty.")
    except pd.errors.ParserError as e:
        raise ValueError(f"Failed to parse CSV file at '{csv_path}': {e}")

    top_20_outbound = [
        {"author_id": author, "tweet_count": count}
        for author, count in outbound_authors_counter.most_common(20)
    ]

    profile_data: Dict[str, Any] = {
        "file_name": csv_path.name,
        "file_path": str(csv_path.relative_to(REPO_ROOT)),
        "sha256": sha256_sum,
        "total_rows": total_rows,
        "columns": column_names,
        "missing_values_per_column": dict(missing_counts),
        "inbound_customer_messages": inbound_count,
        "outbound_brand_messages": outbound_count,
        "top_20_outbound_authors": top_20_outbound,
    }

    # Ensure output results directory exists
    profile_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(profile_output_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

    # Print summary results to console (without printing message text)
    print("\n================ DATASET EXPLORATION PROFILE ================")
    print(f"File Path                 : {csv_path.relative_to(REPO_ROOT)}")
    print(f"SHA256 Checksum           : {sha256_sum}")
    print(f"Total Rows                : {total_rows:,}")
    print(f"Columns ({len(column_names)})              : {', '.join(column_names)}")
    print(f"Inbound Customer Messages : {inbound_count:,}")
    print(f"Outbound Brand Messages   : {outbound_count:,}")
    print("\nMissing Values Per Column:")
    for col, count in missing_counts.items():
        pct = (count / total_rows) * 100 if total_rows > 0 else 0
        print(f"  - {col:<25}: {count:,} ({pct:.2f}%)")
    
    print("\nTop 20 Outbound Authors (Brand Support Accounts):")
    for rank, item in enumerate(top_20_outbound, start=1):
        print(f"  {rank:2d}. {item['author_id']:<20} : {item['tweet_count']:,} tweets")

    print(f"\nSaved detailed profile to: {profile_output_path.relative_to(REPO_ROOT)}")
    print("=============================================================")

    return profile_data


if __name__ == "__main__":
    try:
        inspect_dataset()
    except Exception as err:
        print(f"Error inspecting dataset: {err}", file=sys.stderr)
        sys.exit(1)
