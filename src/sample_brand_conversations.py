"""
Phase 1 Brand Conversation Sampling & Transcript Extraction

Features:
1. Replay Mode (--replay): Re-extracts exact source IDs from original manifest (v1) without resampling.
2. Separate Quality & Structural Flags:
   - structural_completeness (is_complete)
   - suspected_multipart (detects continuation markers like '1/2', '/1', lowercase starts)
   - partial_text (detects trailing truncation like '...')
   - external_context_required (detects t.co URLs, DM requests, screenshots)
3. Privacy Redaction: Handles customer handles (@username), bare customer names, emails, phone numbers, and credit card flags.
"""

import os
import re
import hashlib
import sys
import json
import uuid
import sqlite3
import argparse
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Optional, Tuple
import pandas as pd

from src.inspect_dataset import normalize_inbound_series

# Path resolution relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = REPO_ROOT / "dataset" / "twcs" / "twcs.csv"
OUTPUT_DIR = REPO_ROOT / "results" / "brand_review"
CACHE_DIR = REPO_ROOT / "data" / "cache"
DB_PATH = CACHE_DIR / "twcs_index.sqlite"

MANIFEST_V1_PATH = OUTPUT_DIR / "sampling_manifest_v1.json"
MANIFEST_CURRENT_PATH = OUTPUT_DIR / "sampling_manifest.json"

CANDIDATES = ["SpotifyCares", "AppleSupport", "AskPlayStation"]
RANDOM_SEED = 42
TARGET_COMPLETE_PER_BRAND = 30
CHUNK_SIZE = 100_000
CURRENT_SCHEMA_VERSION = "2.0"


def _safe_relpath(path: Path) -> str:
    """Returns path relative to REPO_ROOT if possible, otherwise the full path."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Ensures cache directory exists and returns a SQLite connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA256 hex digest of a file in binary chunks."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            block = f.read(1 << 20)  # 1 MiB
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


def _normalize_row_for_comparison(
    author_id: Any,
    inbound: Any,
    created_at: Any,
    text: Any,
    resp_id: Any,
    in_resp_id: Any,
) -> Tuple[str, int, str, str, Optional[str], Optional[str]]:
    """Normalizes tweet fields into a canonical tuple for exact duplicate and conflict checking."""
    return (
        str(author_id) if pd.notna(author_id) and author_id is not None else "",
        int(inbound),
        str(created_at) if pd.notna(created_at) and created_at is not None else "",
        str(text) if pd.notna(text) and text is not None else "",
        str(resp_id).strip() if pd.notna(resp_id) and resp_id is not None and str(resp_id).strip() != "" else None,
        str(in_resp_id).strip() if pd.notna(in_resp_id) and in_resp_id is not None and str(in_resp_id).strip() != "" else None,
    )


def validate_sqlite_index(
    db_path: Path,
    expected_csv_checksum: Optional[str] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates SQLite database index provenance, schema compatibility, and build integrity.

    Checks:
    1. Database file exists and is a valid file.
    2. Required tables ('tweets', 'index_metadata') exist.
    3. 'build_completed' flag in index_metadata is '1'.
    4. 'schema_version' matches CURRENT_SCHEMA_VERSION.
    5. 'source_csv_sha256' matches expected_csv_checksum (if provided).
    6. Stored 'row_count' matches actual count of rows in 'tweets' table.

    Returns:
        (is_valid: bool, reason: str, metadata: Dict[str, Any])
    """
    if not db_path.exists() or not db_path.is_file():
        return False, f"Database file not found at '{db_path}'", {}

    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check table existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        required_tables = {"tweets", "index_metadata"}
        if not required_tables.issubset(existing_tables):
            return False, f"Missing required tables (found: {sorted(existing_tables)})", {}

        # Fetch all metadata
        cursor.execute("SELECT key, value FROM index_metadata")
        metadata = {row["key"]: row["value"] for row in cursor.fetchall()}

        # 1. build_completed check
        if metadata.get("build_completed") != "1":
            return False, "Index build was interrupted or not completed (build_completed != '1')", metadata

        # 2. schema_version check
        stored_schema = metadata.get("schema_version")
        if stored_schema != CURRENT_SCHEMA_VERSION:
            return (
                False,
                f"Incompatible schema version: found {stored_schema!r}, expected {CURRENT_SCHEMA_VERSION!r}",
                metadata,
            )

        # 3. source_csv_sha256 check
        stored_checksum = metadata.get("source_csv_sha256")
        if not stored_checksum:
            return False, "Missing source_csv_sha256 in index metadata", metadata

        if expected_csv_checksum and stored_checksum != expected_csv_checksum:
            return (
                False,
                f"Stale source CSV checksum (stored {stored_checksum[:12]}..., expected {expected_csv_checksum[:12]}...)",
                metadata,
            )

        # 4. row_count check against actual table count
        stored_row_count_str = metadata.get("row_count")
        if stored_row_count_str is None or not stored_row_count_str.isdigit():
            return False, f"Missing or invalid stored row_count: {stored_row_count_str!r}", metadata

        stored_row_count = int(stored_row_count_str)
        cursor.execute("SELECT count(*) FROM tweets")
        actual_row_count = cursor.fetchone()[0]

        if stored_row_count != actual_row_count:
            return (
                False,
                f"Stored row count ({stored_row_count}) does not match actual database count ({actual_row_count})",
                metadata,
            )

        return True, "Index validated successfully", metadata
    except Exception as exc:
        return False, f"Error validating SQLite database: {exc}", {}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def build_sqlite_index(
    csv_path: Path = DEFAULT_DATASET_PATH,
    db_path: Path = DB_PATH,
    force_rebuild: bool = False,
    reject_conflicts: bool = False,
) -> Dict[str, Any]:
    """
    Builds a disk-backed SQLite database index from the TWCS CSV using a temporary database.
    Replaces the existing index atomically only after successful validation.

    Integrity guarantees:
    1. Reuses shared strict inbound parser (normalize_inbound_series). Unexpected values raise an error.
    2. Compares all relevant fields for conflicting tweet IDs (no last-write-wins).
    3. Deduplicates identical duplicate rows, recording counts.
    4. Quarantines (or rejects) conflicting duplicate rows in quarantined_tweets.
    5. Validates build_completed, schema_version, source checksum, and row counts before replacing.
    6. Preserves previous database if rebuild fails.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: '{csv_path}'")

    csv_checksum = compute_file_sha256(csv_path)

    if not force_rebuild and db_path.exists():
        is_valid, reason, meta = validate_sqlite_index(db_path, expected_csv_checksum=csv_checksum)
        if is_valid:
            print(
                f"Using existing SQLite index at '{_safe_relpath(db_path)}' "
                f"({meta.get('row_count', '0')} rows, checksum verified).",
                flush=True
            )
            return meta
        else:
            if "checksum mismatch" in reason.lower() or "stale" in reason.lower():
                print(f"  Source CSV checksum mismatch ({reason}). Rebuilding index.", flush=True)
            else:
                print(f"  Existing index invalid ({reason}). Rebuilding index.", flush=True)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_id = uuid.uuid4().hex[:8]
    temp_db_path = db_path.with_name(f"{db_path.stem}.tmp_{temp_id}.sqlite")
    if temp_db_path.exists():
        try:
            temp_db_path.unlink()
        except Exception:
            pass

    print(f"Building disk-backed SQLite index at temporary location '{_safe_relpath(temp_db_path)}'...", flush=True)
    temp_conn = None
    try:
        temp_conn = sqlite3.connect(str(temp_db_path))
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute("PRAGMA synchronous = OFF")
        temp_cursor.execute("PRAGMA journal_mode = MEMORY")

        temp_cursor.execute("""
            CREATE TABLE tweets (
                tweet_id TEXT PRIMARY KEY,
                author_id TEXT,
                inbound INTEGER,
                created_at TEXT,
                text TEXT,
                response_tweet_id TEXT,
                in_response_to_tweet_id TEXT
            )
        """)
        temp_cursor.execute("""
            CREATE TABLE quarantined_tweets (
                tweet_id TEXT,
                author_id TEXT,
                inbound INTEGER,
                created_at TEXT,
                text TEXT,
                response_tweet_id TEXT,
                in_response_to_tweet_id TEXT,
                quarantine_reason TEXT,
                quarantined_at TEXT
            )
        """)
        temp_cursor.execute("""
            CREATE TABLE index_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        temp_conn.commit()

        dtype_spec = {
            "tweet_id": str,
            "author_id": str,
            "response_tweet_id": str,
            "in_response_to_tweet_id": str,
            "created_at": str,
            "text": str,
        }

        reader = pd.read_csv(csv_path, chunksize=CHUNK_SIZE, dtype=dtype_spec)
        inserted_rows = 0
        identical_duplicates_count = 0
        conflicting_duplicates_count = 0
        seen_tweet_ids: Set[str] = set()

        for chunk in reader:
            # Strict inbound normalization: reuse shared parser. Unexpected values raise ValueError!
            inbound_bool = normalize_inbound_series(chunk["inbound"])
            chunk["inbound_int"] = inbound_bool.astype(int)

            chunk["resp_id"] = chunk["response_tweet_id"].where(pd.notna(chunk["response_tweet_id"]), None)
            chunk["in_resp_id"] = chunk["in_response_to_tweet_id"].where(pd.notna(chunk["in_response_to_tweet_id"]), None)

            records_to_insert = []
            quarantine_records = []
            chunk_cache: Dict[str, Tuple[str, int, str, str, Optional[str], Optional[str]]] = {}

            for row in chunk[["tweet_id", "author_id", "inbound_int", "created_at", "text", "resp_id", "in_resp_id"]].itertuples(index=False, name=None):
                tid = str(row[0])
                norm_current = _normalize_row_for_comparison(row[1], row[2], row[3], row[4], row[5], row[6])

                if tid in chunk_cache:
                    prev = chunk_cache[tid]
                    if norm_current == prev:
                        identical_duplicates_count += 1
                    else:
                        conflicting_duplicates_count += 1
                        if reject_conflicts:
                            raise ValueError(f"Conflicting duplicate tweet ID detected in CSV: {tid}")
                        quarantine_records.append((
                            tid, norm_current[0], norm_current[1], norm_current[2], norm_current[3],
                            norm_current[4], norm_current[5], "CONFLICTING_DUPLICATE_TWEET_ID", datetime.now().isoformat()
                        ))
                elif tid in seen_tweet_ids:
                    temp_cursor.execute(
                        "SELECT author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id FROM tweets WHERE tweet_id = ?",
                        (tid,)
                    )
                    db_row = temp_cursor.fetchone()
                    if db_row:
                        prev = _normalize_row_for_comparison(db_row[0], db_row[1], db_row[2], db_row[3], db_row[4], db_row[5])
                    else:
                        prev = None

                    if prev is not None and norm_current == prev:
                        identical_duplicates_count += 1
                    else:
                        conflicting_duplicates_count += 1
                        if reject_conflicts:
                            raise ValueError(f"Conflicting duplicate tweet ID detected in CSV: {tid}")
                        quarantine_records.append((
                            tid, norm_current[0], norm_current[1], norm_current[2], norm_current[3],
                            norm_current[4], norm_current[5], "CONFLICTING_DUPLICATE_TWEET_ID", datetime.now().isoformat()
                        ))
                else:
                    seen_tweet_ids.add(tid)
                    chunk_cache[tid] = norm_current
                    records_to_insert.append((
                        tid, norm_current[0], norm_current[1], norm_current[2], norm_current[3],
                        norm_current[4], norm_current[5]
                    ))

            if records_to_insert:
                temp_cursor.executemany("""
                    INSERT INTO tweets (
                        tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, records_to_insert)
                inserted_rows += len(records_to_insert)

            if quarantine_records:
                temp_cursor.executemany("""
                    INSERT INTO quarantined_tweets (
                        tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id,
                        quarantine_reason, quarantined_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, quarantine_records)

            temp_conn.commit()
            print(f"  Indexed {inserted_rows:,} rows...", flush=True)

        if conflicting_duplicates_count > 0:
            print(
                f"  Warning: {conflicting_duplicates_count} conflicting duplicate tweet IDs detected "
                f"(quarantined, original row preserved without last-write-wins).",
                flush=True
            )
        if identical_duplicates_count > 0:
            print(f"  Deduplicated {identical_duplicates_count:,} identical duplicate rows.", flush=True)

        print("Creating indexes on temporary SQLite database...", flush=True)
        temp_cursor.execute("CREATE INDEX IF NOT EXISTS idx_author_id ON tweets(author_id)")
        temp_cursor.execute("CREATE INDEX IF NOT EXISTS idx_inbound ON tweets(inbound)")
        temp_cursor.execute("CREATE INDEX IF NOT EXISTS idx_in_response_to ON tweets(in_response_to_tweet_id)")

        # Verify actual counts
        temp_cursor.execute("SELECT count(*) FROM tweets")
        actual_count = temp_cursor.fetchone()[0]
        if actual_count != inserted_rows:
            raise RuntimeError(f"Database row count mismatch during build: expected {inserted_rows}, got {actual_count}")

        # Store metadata
        temp_cursor.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES (?, ?)", ("source_csv_sha256", csv_checksum))
        temp_cursor.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES (?, ?)", ("schema_version", CURRENT_SCHEMA_VERSION))
        temp_cursor.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES (?, ?)", ("row_count", str(actual_count)))
        temp_cursor.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES (?, ?)", ("identical_duplicates_count", str(identical_duplicates_count)))
        temp_cursor.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES (?, ?)", ("conflicting_duplicates_count", str(conflicting_duplicates_count)))
        temp_cursor.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES (?, ?)", ("build_timestamp", datetime.now().isoformat()))
        # build_completed is written ONLY at the very end
        temp_cursor.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES (?, ?)", ("build_completed", "1"))
        temp_conn.commit()

        temp_conn.close()
        temp_conn = None

        # Validate temporary database before replacing the target database
        is_valid, reason, validated_meta = validate_sqlite_index(temp_db_path, expected_csv_checksum=csv_checksum)
        if not is_valid:
            raise RuntimeError(f"Temporary SQLite index failed validation: {reason}")

        # Atomically replace target database
        os.replace(temp_db_path, db_path)
        print(
            f"SQLite index build complete and atomically replaced at '{_safe_relpath(db_path)}' "
            f"({actual_count:,} rows, checksum={csv_checksum[:12]}...).",
            flush=True
        )
        return validated_meta

    except Exception as exc:
        if temp_conn is not None:
            try:
                temp_conn.close()
            except Exception:
                pass
        if temp_db_path.exists():
            try:
                temp_db_path.unlink()
            except Exception:
                pass
        raise exc


def parse_created_at(created_at_str: str) -> datetime:
    """Parses Twitter API created_at timestamp string for chronological sorting."""
    try:
        return datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return datetime.min


def redact_sensitive_info(text: str, candidate_brands: List[str] = CANDIDATES) -> str:
    """
    Redacts customer handles, contextual bare customer usernames, emails, phone numbers,
    and dataset privacy placeholders. Preserves brand handles, device names, software versions,
    and error codes. Fully idempotent.
    """
    if not text:
        return text

    brand_handles = {b.lower() for b in candidate_brands} | {
        "spotifycares", "spotify", "spotifyusa", "spotifyuk", "spotifyhelp",
        "spotifystatus", "spotifyjobs", "applesupport", "askplaystation",
        "amazonhelp", "tmobilehelp", "uber_support", "microsofthelps"
    }

    # 1. Dataset privacy placeholders normalization & idempotency protection
    text = re.sub(r'id::\d+__credit_card__:', '[CREDIT_CARD_REDACTED]:', text)
    text = re.sub(r'\b__credit_card__\b', '[CREDIT_CARD_REDACTED]', text)
    text = re.sub(r'\b__email__\b', '[EMAIL_REDACTED]', text)
    text = re.sub(r'\b__phone__\b', '[PHONE_REDACTED]', text)

    # 2. Contextual bare-username handling (e.g. "My username is listener_demo96")
    def username_replacer(match: re.Match) -> str:
        prefix = match.group(1)
        val = match.group(2)
        quote = match.group(3) or ""

        # Don't replace if already a placeholder
        if val in {"[CUSTOMER_USERNAME]", "[CUSTOMER_NAME]", "[CUSTOMER_HANDLE]", "@[CUSTOMER_HANDLE]"}:
            return match.group(0)
        if val.startswith("[") and val.endswith("]"):
            return match.group(0)

        lower_val = val.lstrip("@").lower()
        if lower_val in {
            "not", "none", "unknown", "lost", "forgotten", "n/a", "null", "blank",
            "working", "broken", "fine", "ok", "okay", "good", "bad", "active",
            "locked", "disabled", "blocked", "banned", "hacked", "suspended",
            "changed", "new", "old", "same", "different", "invalid", "correct",
            "wrong", "missing", "private", "public", "already", "still"
        }:
            return match.group(0)
        if lower_val in brand_handles or lower_val in {"spotify", "apple", "google", "android", "iphone", "ios", "windows", "mac"}:
            return match.group(0)
        # Avoid error codes
        if re.match(r'^(?:0x[0-9a-fA-F]+|\d{3,4})$', val):
            return match.group(0)

        return f"{prefix}[CUSTOMER_USERNAME]{quote}"

    username_pattern = re.compile(
        r'(\b(?:my\s+)?(?:official\s+)?(?:spotify\s+)?(?:account\s+)?(?:user\s*name|username|screen\s*name|user\s*id|login(?:\s+name|\s+id)?|account(?:\s+name|\s+id)?|handle)\s*(?:is|:|=|-|\bis\s+called)\s*[\'"]?)(@?[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)*)([\'"]?)',
        re.IGNORECASE
    )
    text = username_pattern.sub(username_replacer, text)

    # 3. Emails (must be redacted before customer handles so @domain is not matched as handle)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL_REDACTED]', text)

    # 4. Customer handles (@username) while keeping brand handles intact
    def handle_replacer(match: re.Match) -> str:
        handle_name = match.group(1)
        if handle_name.startswith("[") and handle_name.endswith("]"):
            return match.group(0)
        if handle_name.lower() in brand_handles:
            return f"@{handle_name}"
        return "@[CUSTOMER_HANDLE]"

    text = re.sub(r'@([A-Za-z0-9_]+)', handle_replacer, text)

    # 5. Phone numbers (avoid matching software versions like v8.4.22.857 and error codes)
    text = re.sub(r'(?<![vV\d.])(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)(?!\.\d)', '[PHONE_REDACTED]', text)

    # 6. Bare customer greeting names (e.g., "Hey Vanessa," -> "Hey [CUSTOMER_NAME],")
    reserved_greeting_targets = brand_handles | {
        "spotify", "spotifycares", "apple", "amazon", "google", "playstation",
        "customer_name", "customer_username", "there", "team", "everyone", "guys"
    }

    def greeting_replacer(match: re.Match) -> str:
        greeting = match.group(1)
        name = match.group(2)
        if name.lower() in reserved_greeting_targets:
            return match.group(0)
        return f"{greeting} [CUSTOMER_NAME]"

    text = re.sub(r'\b(Hey|Hi|Hello|Dear)\s+([A-Z][a-z]{2,15})\b', greeting_replacer, text)

    return text


def detect_quality_and_structural_flags(tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes conversation tweets for detailed, separated quality and structural flags:
    - suspected_multipart (bool): continuation markers (1/2, /1, lowercase start without parent)
    - partial_text (bool): trailing truncation ('...')
    - has_url (bool): contains shortened URLs (https://t.co/...)
    - private_handoff (bool): DM/direct-message request detected
    - external_context_required (bool): screenshot mention, or other non-URL external dependency
    """
    suspected_multipart = False
    partial_text = False
    has_url = False
    private_handoff = False
    external_context_required = False

    for t in tweets:
        txt = (t.get("text") or "").strip()
        txt_lower = txt.lower()
        is_inbound = bool(t.get("inbound"))

        # Check for shortened URLs
        if "https://t.co/" in txt or "http://t.co/" in txt:
            has_url = True

        # Check for private handoff (DM requests)
        if "dm us" in txt_lower or "dm me" in txt_lower or "direct message" in txt_lower:
            private_handoff = True

        # Check for other external context needs (screenshots, external instructions)
        if "screenshot" in txt_lower or "screen shot" in txt_lower:
            external_context_required = True

        # Check for partial text / trailing truncation
        if txt.endswith("...") or txt.endswith(" w") or "..." in txt:
            partial_text = True

        # Check for suspected multipart continuation
        if is_inbound:
            if re.search(r'(\b\d/\d\b|\b/\d\b|\b1/\b|\b2/\b)', txt):
                suspected_multipart = True
            # Starts with lowercase continuation without parent link
            if t.get("in_response_to_tweet_id") is None and txt and txt[0].islower() and not txt.startswith("http"):
                suspected_multipart = True

    return {
        "suspected_multipart": suspected_multipart,
        "partial_text": partial_text,
        "has_url": has_url,
        "private_handoff": private_handoff,
        "external_context_required": external_context_required,
    }


def fetch_tweet_by_id(cursor: sqlite3.Cursor, tweet_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single tweet dictionary by tweet_id."""
    cursor.execute(
        "SELECT tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id "
        "FROM tweets WHERE tweet_id = ?",
        (str(tweet_id),)
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None


def fetch_replies_to_tweet(cursor: sqlite3.Cursor, tweet_id: str) -> List[Dict[str, Any]]:
    """Retrieves all tweets responding to a given tweet_id."""
    cursor.execute(
        "SELECT tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id "
        "FROM tweets WHERE in_response_to_tweet_id = ?",
        (str(tweet_id),)
    )
    return [dict(r) for r in cursor.fetchall()]


def find_root_tweet(cursor: sqlite3.Cursor, start_tweet: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, List[str]]:
    """
    Traces backwards along in_response_to_tweet_id to find the root customer tweet.
    Detects missing parents and cycles during ancestor traversal.
    """
    visited: Set[str] = set()
    flags: List[str] = []
    curr = start_tweet

    while curr and curr["in_response_to_tweet_id"]:
        parent_id = str(curr["in_response_to_tweet_id"])
        if parent_id in visited:
            flags.append("CYCLE_DETECTED")
            return curr, False, flags
        visited.add(parent_id)

        parent = fetch_tweet_by_id(cursor, parent_id)
        if not parent:
            flags.append(f"MISSING_PARENT:{parent_id}")
            return curr, False, flags

        curr = parent

    return curr, True, flags


def collect_thread_tree(cursor: sqlite3.Cursor, root_tweet: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool, List[str]]:
    """
    Collects all turns connected to root_tweet using BFS, sorts them chronologically,
    and returns (sorted_tweets, is_complete, flags).
    """
    visited_ids: Set[str] = set()
    tweets_list: List[Dict[str, Any]] = []
    flags: List[str] = []
    is_complete = True

    queue = [root_tweet]

    while queue:
        curr = queue.pop(0)
        tid = curr["tweet_id"]

        if tid in visited_ids:
            flags.append(f"DUPLICATE_TWEET_ID:{tid}")
            is_complete = False
            continue

        visited_ids.add(tid)
        tweets_list.append(curr)

        replies = fetch_replies_to_tweet(cursor, tid)
        for r in replies:
            if r["tweet_id"] not in visited_ids:
                queue.append(r)

    # Sort turns strictly chronologically
    tweets_list.sort(key=lambda t: parse_created_at(t["created_at"]))

    return tweets_list, is_complete, flags


def extract_and_sample_brand_conversations(
    brand: str,
    cursor: sqlite3.Cursor,
    rng: random.Random,
    target_complete: int = TARGET_COMPLETE_PER_BRAND,
    replay_root_ids: Optional[List[str]] = None,
    replay_brand_reply_ids: Optional[Dict[str, str]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts brand conversations.
    If replay_root_ids is provided (Replay Mode), re-extracts exact source root IDs from manifest_v1 without resampling.
    Otherwise, performs uniform conversation sampling starting from unique conversation groups (root tweet IDs).
    """
    print(f"\nExtracting conversation candidates for {brand}...", flush=True)

    if replay_root_ids is not None:
        print(f"  [REPLAY MODE] Extracting {len(replay_root_ids)} exact source root IDs for {brand}...", flush=True)
        unique_root_ids = replay_root_ids
    else:
        cursor.execute(
            "SELECT tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id "
            "FROM tweets WHERE author_id = ? AND inbound = 0 AND in_response_to_tweet_id IS NOT NULL",
            (brand,)
        )
        brand_tweets = [dict(r) for r in cursor.fetchall()]
        print(f"  Found {len(brand_tweets):,} outbound brand replies for {brand}.", flush=True)

        root_map: Dict[str, Tuple[Dict[str, Any], Dict[str, Any], bool, List[str]]] = {}
        for b_tweet in brand_tweets:
            root_tweet, root_complete, root_flags = find_root_tweet(cursor, b_tweet)
            root_id = root_tweet["tweet_id"]
            if root_id not in root_map:
                root_map[root_id] = (root_tweet, b_tweet, root_complete, root_flags)

        unique_root_ids = sorted(list(root_map.keys()))
        print(f"  Identified {len(unique_root_ids):,} unique conversation groups for {brand}.", flush=True)
        rng.shuffle(unique_root_ids)

    sampled_conversations: List[Dict[str, Any]] = []
    manifest_records: List[Dict[str, Any]] = []
    complete_count = 0

    for root_id in unique_root_ids:
        root_tweet = fetch_tweet_by_id(cursor, root_id)
        if not root_tweet:
            print(f"  Warning: root_tweet_id {root_id} not found in database.", flush=True)
            continue

        root_tweet_checked, root_complete, root_flags = find_root_tweet(cursor, root_tweet)
        tweets_seq, tree_complete, tree_flags = collect_thread_tree(cursor, root_tweet)

        all_flags = list(set(root_flags + tree_flags))
        is_complete = root_complete and tree_complete and (len(all_flags) == 0)

        # Compute additional quality flags
        quality_flags = detect_quality_and_structural_flags(tweets_seq)

        conv_id = f"{brand}_CONV_{len(sampled_conversations)+1:03d}"

        # Find brand reply tweet ID: in replay mode, use original manifest ID if available
        if replay_brand_reply_ids and root_id in replay_brand_reply_ids:
            brand_reply_id = replay_brand_reply_ids[root_id]
        else:
            brand_replies = [t for t in tweets_seq if t["author_id"].lower() == brand.lower()]
            brand_reply_id = brand_replies[0]["tweet_id"] if brand_replies else tweets_seq[-1]["tweet_id"]

        conv_item = {
            "conversation_id": conv_id,
            "brand": brand,
            "root_tweet_id": root_id,
            "is_complete": is_complete,
            "flags": all_flags,
            "quality_flags": quality_flags,
            "tweets": tweets_seq
        }

        manifest_item = {
            "brand": brand,
            "conversation_id": conv_id,
            "root_tweet_id": root_id,
            "brand_reply_tweet_id": brand_reply_id,
            "tweet_count": len(tweets_seq),
            "is_complete": is_complete,
            "flags": all_flags,
            "quality_flags": quality_flags
        }

        sampled_conversations.append(conv_item)
        manifest_records.append(manifest_item)

        if is_complete:
            complete_count += 1

        if replay_root_ids is None:
            if complete_count >= target_complete and len(sampled_conversations) >= 30:
                break

    print(f"  Sampled {len(sampled_conversations)} total conversations for {brand} ({complete_count} complete).", flush=True)
    return sampled_conversations, manifest_records


def generate_markdown_transcript(brand: str, conversations: List[Dict[str, Any]], output_md_path: Path) -> None:
    """
    Writes formatted, redacted conversation transcripts to a Markdown file.
    """
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(f"# Brand Conversation Transcripts: {brand}\n\n")
        f.write(f"**Candidate Brand**: `{brand}`  \n")
        f.write(f"**Total Sampled Conversations**: `{len(conversations)}`  \n")
        f.write(f"**Sampling Seed**: `{RANDOM_SEED}`  \n\n")
        f.write("---\n\n")

        for conv in conversations:
            conv_id = conv["conversation_id"]
            is_complete = conv["is_complete"]
            flags = conv["flags"]
            q_flags = conv.get("quality_flags", {})
            tweets = conv["tweets"]

            status_str = "COMPLETE" if is_complete else f"INCOMPLETE ({', '.join(flags)})"
            
            f.write(f"## Conversation ID: `{conv_id}`\n\n")
            f.write(f"- **Status**: `{status_str}`\n")
            f.write(f"- **Root Tweet ID**: `{conv['root_tweet_id']}`\n")
            f.write(f"- **Turns Count**: `{len(tweets)}` turn(s)\n")
            f.write(
                f"- **Quality Flags**: `multipart={q_flags.get('suspected_multipart', False)}`, "
                f"`partial_text={q_flags.get('partial_text', False)}`, "
                f"`url={q_flags.get('has_url', False)}`, "
                f"`dm={q_flags.get('private_handoff', False)}`, "
                f"`external_context={q_flags.get('external_context_required', False)}`\n\n"
            )
            f.write("### Transcript\n\n")

            for tweet in tweets:
                author = tweet["author_id"]
                is_inbound = bool(tweet["inbound"])
                tweet_id = tweet["tweet_id"]
                created_at = tweet["created_at"]
                raw_text = tweet["text"]
                redacted_text = redact_sensitive_info(raw_text)

                if is_inbound:
                    role_label = f"👤 Customer (author_id: `@[CUSTOMER_HANDLE]`)"
                else:
                    role_label = f"🏢 Brand ({author})"

                f.write(f"**{role_label}** | *Tweet ID*: `{tweet_id}` | *Time*: `{created_at}`  \n")
                f.write(f"> {redacted_text}\n\n")

            f.write("---\n\n")


def generate_review_scores_csv(
    all_manifest_records: List[Dict[str, Any]],
    output_csv_path: Path,
    force_overwrite: bool = False
) -> None:
    """
    Generates or updates review_scores.csv preserving existing human annotations.

    Merge strategy:
    - Uses root_tweet_id as the stable merge key (not CONV_xxx labels which may change).
    - If the file already exists and force_overwrite is False, existing rows are
      loaded and human-entered values are preserved for matching root_tweet_ids.
      Also supports legacy files matching by conversation_id.
    - New conversations (not in existing file) get empty review columns appended.
    - If force_overwrite is True, existing data is discarded and regenerated.

    Columns: brand, conversation_id, root_tweet_id, issue_category,
             useful_public_advice, private_handoff, outcome_confirmed,
             time_sensitive_advice, notes
    """
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    HUMAN_COLS = [
        "issue_category", "useful_public_advice", "private_handoff",
        "outcome_confirmed", "time_sensitive_advice", "notes"
    ]

    # Load existing annotations keyed by root_tweet_id (with conversation_id fallback)
    existing_by_root: Dict[str, Dict[str, str]] = {}
    existing_by_conv: Dict[str, Dict[str, str]] = {}
    if output_csv_path.exists() and not force_overwrite:
        try:
            existing_df = pd.read_csv(output_csv_path, dtype=str, keep_default_na=False)
            for _, row in existing_df.iterrows():
                human_vals = {col: str(row.get(col, "")) for col in HUMAN_COLS}
                has_any = any(v.strip() for v in human_vals.values())
                if has_any:
                    if "root_tweet_id" in existing_df.columns and row.get("root_tweet_id"):
                        existing_by_root[str(row["root_tweet_id"])] = human_vals
                    if "conversation_id" in existing_df.columns and row.get("conversation_id"):
                        existing_by_conv[str(row["conversation_id"])] = human_vals

            preserved_total = len(existing_by_root) or len(existing_by_conv)
            if preserved_total:
                print(
                    f"  Preserving {preserved_total} existing human annotation(s) "
                    f"from '{output_csv_path.name}'.",
                    flush=True
                )
        except Exception as e:
            print(f"  Warning: could not read existing review sheet: {e}", flush=True)

    rows = []
    for item in all_manifest_records:
        root_id = str(item["root_tweet_id"])
        conv_id = str(item["conversation_id"])
        row: Dict[str, str] = {
            "brand": item["brand"],
            "conversation_id": conv_id,
            "root_tweet_id": root_id,
        }
        # Merge existing human annotations if available (keyed by stable root_id, fallback conv_id)
        preserved = existing_by_root.get(root_id) or existing_by_conv.get(conv_id, {})
        for col in HUMAN_COLS:
            row[col] = preserved.get(col, "")
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_csv_path, index=False, encoding="utf-8")

    preserved_count = sum(1 for r in rows if any(r[c].strip() for c in HUMAN_COLS))
    print(
        f"Wrote review sheet at: '{_safe_relpath(output_csv_path)}' "
        f"({len(df)} rows, {preserved_count} with preserved annotations).",
        flush=True
    )


def main():
    """Main execution entrypoint with argument parsing for --replay mode."""
    parser = argparse.ArgumentParser(description="Brand Conversation Sampling & Extraction")
    parser.add_argument("--replay", action="store_true", help="Replay mode: re-extract exact source IDs from manifest v1 without resampling")
    args = parser.parse_args()

    replay_mode = args.replay

    print("================ BRAND CONVERSATION SAMPLING ================", flush=True)
    print(f"Candidate Brands  : {', '.join(CANDIDATES)}")
    print(f"Sampling Seed     : {RANDOM_SEED}")
    print(f"Replay Mode       : {replay_mode}")
    print(f"Output Directory  : {_safe_relpath(OUTPUT_DIR)}")

    build_sqlite_index(DEFAULT_DATASET_PATH, DB_PATH)

    conn = get_db_connection(DB_PATH)
    cursor = conn.cursor()

    rng = random.Random(RANDOM_SEED)
    all_manifest_records: List[Dict[str, Any]] = []

    replay_roots_by_brand: Dict[str, List[str]] = {}
    replay_brand_replies_by_brand: Dict[str, Dict[str, str]] = {}
    if replay_mode:
        if not MANIFEST_V1_PATH.exists():
            raise FileNotFoundError(f"Cannot run replay mode: original manifest '{MANIFEST_V1_PATH}' not found.")
        with open(MANIFEST_V1_PATH, "r", encoding="utf-8") as f:
            v1_data = json.load(f)
        for c in v1_data.get("conversations", []):
            b = c["brand"]
            replay_roots_by_brand.setdefault(b, []).append(c["root_tweet_id"])
            if "brand_reply_tweet_id" in c:
                replay_brand_replies_by_brand.setdefault(b, {})[c["root_tweet_id"]] = c["brand_reply_tweet_id"]

    for brand in CANDIDATES:
        replay_list = replay_roots_by_brand.get(brand) if replay_mode else None
        replay_br_ids = replay_brand_replies_by_brand.get(brand) if replay_mode else None
        conversations, manifest_records = extract_and_sample_brand_conversations(
            brand, cursor, rng, target_complete=TARGET_COMPLETE_PER_BRAND,
            replay_root_ids=replay_list, replay_brand_reply_ids=replay_br_ids
        )
        all_manifest_records.extend(manifest_records)

        md_file_path = OUTPUT_DIR / f"{brand}.md"
        generate_markdown_transcript(brand, conversations, md_file_path)
        print(f"  Wrote transcript file: '{_safe_relpath(md_file_path)}'", flush=True)

    conn.close()

    manifest_path = MANIFEST_CURRENT_PATH
    manifest_data = {
        "sampling_seed": RANDOM_SEED,
        "replay_mode": replay_mode,
        "candidate_brands": CANDIDATES,
        "target_complete_per_brand": TARGET_COMPLETE_PER_BRAND,
        "total_conversations_sampled": len(all_manifest_records),
        "conversations": all_manifest_records
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"\nWrote sampling manifest to: '{_safe_relpath(manifest_path)}'", flush=True)

    review_csv_path = OUTPUT_DIR / "review_scores.csv"
    generate_review_scores_csv(all_manifest_records, review_csv_path)

    print("=============================================================", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"Error during brand conversation sampling: {err}", file=sys.stderr)
        sys.exit(1)
