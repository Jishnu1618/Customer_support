"""
Phase 2: Spotify Historical Corpus, Development Inputs, and Held-Out Evaluation Pool Preparation

Features:
1. Provenance Preservation:
   - Preserves all previous review manifests and human review files.
   - Excludes any conversation group ever inspected in brand review from eval_pool eligibility.
   - Incomplete original records treated as audit records, not valid pairs.
2. Eligible Record Construction:
   - Identifies Spotify replies whose direct parent is a customer turn.
   - Preserves full conversation groups for split isolation.
   - Constructs model context strictly from the target customer's ancestor path.
   - Applies privacy redaction to all exported text.
3. Eligibility & Quality Rules:
   - Excludes structurally incomplete threads, cycles, missing parents.
   - Language determination on target customer message and ancestor context (rule-based lexical stopwords & script).
   - Requires interpretable support content (excludes uninterpretable fragments).
4. Leakage Prevention:
   - Keeps full conversation groups in one partition.
   - Exact duplicate customer inquiries deduplicated across groups.
   - Near-duplicate candidate detection with character 4-gram / token overlap.
   - Held-out brand replies completely separated from model inputs.
5. Deterministic Partitioning:
   - Historical corpus: target 3,000 groups.
   - Development set: 50 messages from separate groups.
   - Evaluation pool: up to 1,000 groups.
   - Deterministic sorting by stable IDs prior to shuffle with seed 42.
"""

import os
import re
import sys
import json
import random
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Optional, Tuple
from collections import Counter, defaultdict

# Path resolution relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = REPO_ROOT / "dataset" / "twcs" / "twcs.csv"
CACHE_DIR = REPO_ROOT / "data" / "cache"
DB_PATH = CACHE_DIR / "twcs_index.sqlite"

OUTPUT_DATA_DIR = REPO_ROOT / "data" / "processed" / "v2"
OUTPUT_MANIFEST_DIR = REPO_ROOT / "data" / "manifests" / "v2"
OUTPUT_REPORT_DIR = REPO_ROOT / "results" / "phase2_v2"
BRAND_REVIEW_DIR = REPO_ROOT / "results" / "brand_review"

# Targets & parameters
TARGET_HISTORICAL = 3000
TARGET_DEV = 50
TARGET_EVAL_POOL = 1000
RANDOM_SEED = 42
PREPROCESSING_VERSION = "2.0"
BRAND_NAME = "SpotifyCares"

# Protected reference files that must never be altered or overwritten
PROTECTED_FILES = [
    REPO_ROOT / "results" / "brand_review" / "original_sampling_manifest.json",
    REPO_ROOT / "results" / "brand_review" / "sampling_manifest_original_uploaded.json",
    REPO_ROOT / "results" / "brand_review" / "sampling_manifest_v1.json",
    REPO_ROOT / "results" / "brand_review" / "sampling_manifest.json",
    REPO_ROOT / "results" / "brand_review" / "review_scores.csv",
    REPO_ROOT / "data" / "processed" / "spotify_knowledge.jsonl",
    REPO_ROOT / "data" / "processed" / "dev_inputs.jsonl",
    REPO_ROOT / "data" / "processed" / "eval_pool_inputs.jsonl",
    REPO_ROOT / "data" / "manifests" / "split_manifest.jsonl",
    REPO_ROOT / "results" / "data_profile.json",
]


def hash_protected_files() -> Dict[str, str]:
    """Computes SHA-256 for all protected reference files."""
    hashes = {}
    for pf in PROTECTED_FILES:
        if pf.exists():
            hashes[str(pf)] = compute_file_sha256(pf)
    return hashes


def verify_protected_files(initial_hashes: Dict[str, str]) -> Dict[str, bool]:
    """Verifies that protected files were never modified or overwritten."""
    results = {}
    for fpath_str, orig_hash in initial_hashes.items():
        p = Path(fpath_str)
        if not p.exists():
            raise RuntimeError(f"CRITICAL: Protected file was deleted: {fpath_str}")
        curr_hash = compute_file_sha256(p)
        if curr_hash != orig_hash:
            raise RuntimeError(
                f"CRITICAL: Protected file modified! {fpath_str} (expected {orig_hash}, got {curr_hash})"
            )
        results[fpath_str] = True
    return results

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.sample_brand_conversations import (
    get_db_connection,
    fetch_tweet_by_id,
    fetch_replies_to_tweet,
    find_root_tweet,
    collect_thread_tree,
    detect_quality_and_structural_flags,
    redact_sensitive_info,
    compute_file_sha256,
    _safe_relpath,
    build_sqlite_index,
    validate_sqlite_index,
    CURRENT_SCHEMA_VERSION,
)
from src.context_builder import (
    build_ancestor_path,
    assign_anonymous_actor_ids,
    build_model_context,
)
from src.duplicate_detector import (
    normalize_inquiry,
    get_effective_inquiry,
    find_duplicate_pairs_inverted_index,
    build_transitive_clusters,
    load_exclusion_history,
    propagate_restrictions_to_clusters,
)
from src.language_filter import (
    detect_language_state,
    is_contextually_interpretable,
    export_human_review_sheet,
    LANGUAGE_STATE_ENGLISH,
    LANGUAGE_STATE_NON_ENGLISH,
    LANGUAGE_STATE_UNCERTAIN,
)



def validate_or_rebuild_index(
    db_path: Path = DB_PATH,
    csv_path: Path = DEFAULT_DATASET_PATH,
    rebuild_if_invalid: bool = True,
) -> Dict[str, Any]:
    """
    Compares current CSV checksum with SQLite index stored checksum and validates
    provenance and build integrity before extraction.
    Rebuilds or rejects stale, incomplete, or incompatible indexes.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Source CSV dataset not found at '{csv_path}'")

    current_csv_checksum = compute_file_sha256(csv_path)

    if not db_path.exists():
        if not rebuild_if_invalid:
            raise FileNotFoundError(f"SQLite index not found at '{db_path}'")
        print(f"SQLite index not found at '{_safe_relpath(db_path)}'. Building index...", flush=True)
        return build_sqlite_index(csv_path=csv_path, db_path=db_path)

    is_valid, reason, metadata = validate_sqlite_index(db_path, expected_csv_checksum=current_csv_checksum)
    if is_valid:
        print(
            f"SQLite index validated ({metadata.get('row_count')} rows, schema v{metadata.get('schema_version')}, checksum verified).",
            flush=True
        )
        return metadata

    if not rebuild_if_invalid:
        raise ValueError(f"SQLite index validation failed: {reason}")

    print(f"SQLite index invalid ({reason}). Rebuilding index from '{_safe_relpath(csv_path)}'...", flush=True)
    metadata = build_sqlite_index(csv_path=csv_path, db_path=db_path, force_rebuild=True)
    is_valid, reason, metadata = validate_sqlite_index(db_path, expected_csv_checksum=current_csv_checksum)
    if not is_valid:
        raise RuntimeError(f"Rebuilt index failed validation: {reason}")
    return metadata


def load_review_exclusion_root_ids() -> Set[str]:
    """
    Loads all root_tweet_ids inspected in any brand-review manifest or review sheet.
    These conversation groups are strictly excluded from eval_pool eligibility.
    """
    excluded_roots: Set[str] = set()
    manifest_files = [
        BRAND_REVIEW_DIR / "original_sampling_manifest.json",
        BRAND_REVIEW_DIR / "sampling_manifest_original_uploaded.json",
        BRAND_REVIEW_DIR / "sampling_manifest_v1.json",
        BRAND_REVIEW_DIR / "sampling_manifest.json",
    ]

    for mf in manifest_files:
        if mf.exists():
            try:
                with open(mf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for c in data.get("conversations", []):
                    if c.get("brand") == BRAND_NAME and "root_tweet_id" in c:
                        excluded_roots.add(str(c["root_tweet_id"]))
            except Exception as e:
                print(f"Warning reading {mf.name}: {e}", file=sys.stderr)

    review_scores_path = BRAND_REVIEW_DIR / "review_scores.csv"
    if review_scores_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(review_scores_path, dtype=str, keep_default_na=False)
            if "root_tweet_id" in df.columns:
                for r in df["root_tweet_id"]:
                    if r.strip():
                        excluded_roots.add(str(r.strip()))
        except Exception as e:
            print(f"Warning reading review_scores.csv: {e}", file=sys.stderr)

    return excluded_roots


ENGLISH_STOPWORDS = {
    'the', 'i', 'to', 'a', 'and', 'is', 'in', 'it', 'you', 'that', 'of', 'for', 'on', 'are',
    'with', 'as', 'at', 'be', 'this', 'have', 'from', 'my', 'me', 'not', 'can', 'help', 'please',
    'why', 'does', 'app', 'play', 'playlist', 'account', 'music', 'listening', 'offline', 'update',
    'song', 'working', 'phone', 'device', 'when', 'what', 'how', 'do', 'so', 'but', 'just', 'like',
    'all', 'or', 'an', 'if', 'get', 'no', 'we', 'your', 'was', 'am', 'im', 'cant', 'wont',
    'has', 'had', 'been', 'there', 'they', 'their', 'them', 'any', 'some', 'more', 'new', 'now',
    'see', 'know', 'want', 'think', 'good', 'bad', 'fix', 'tried', 'trying', 'issue', 'problem',
    'still', 'again', 'after', 'before', 'premium', 'spotify', 'hear', 'sound', 'tracks', 'album',
    'artist', 'download', 'offline', 'logged', 'login', 'pass', 'password', 'card', 'payment',
    'charge', 'billed', 'subscription', 'student', 'family', 'cancel', 'reset', 'error', 'crashed'
}

NON_ENGLISH_STOPWORDS = {
    # Spanish & Portuguese
    'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'que', 'en', 'por', 'para', 'con',
    'es', 'son', 'estoy', 'esta', 'está', 'mis', 'cuenta', 'cancion', 'canción', 'musica',
    'música', 'ayuda', 'como', 'cómo', 'mas', 'más', 'pero', 'porque', 'yo', 'tu', 'su',
    'nao', 'não', 'uma', 'umas', 'com', 'minha', 'meu', 'voce', 'você', 'ja', 'já', 'pra',
    'dele', 'dela', 'obrigado', 'gracias', 'hola', 'olá', 'favor', 'porfavor', 'puedo', 'consigo',
    'tem', 'tenho', 'quero', 'ajuda', 'problema', 'musicas', 'músicas', 'tocando',
    # French
    'le', 'les', 'du', 'des', 'une', 'et', 'dans', 'sur', 'pour', 'avec', 'je', 'ce', 'pas',
    'qui', 'mon', 'mes', 'est', 'suis', 'ne', 'merci', 'bonjour', 'compte',
    # German
    'und', 'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'nicht', 'mit', 'auf',
    'fur', 'für', 'ist', 'ich', 'sie', 'es', 'kann', 'mein', 'meine', 'bitte', 'hilfe',
    # Italian
    'il', 'la', 'che', 'non', 'sono', 'per', 'una', 'della', 'dello', 'mio', 'mia', 'ciao'
}


def detect_english_language(
    text: str,
    ancestor_turns: Optional[List[Dict[str, Any]]] = None
) -> Tuple[bool, float, str, bool]:
    """
    Determines whether a message is in English based on lexical stopwords, context, and script.
    Evaluates target customer message and required customer context only (never future reply).
    Returns (is_english, language_heuristic_score, reason, is_uncertain).
    """
    state, score, reason = detect_language_state(text, ancestor_turns)
    is_eng = (state == LANGUAGE_STATE_ENGLISH)
    is_unc = (state == LANGUAGE_STATE_UNCERTAIN)
    return is_eng, score, reason, is_unc


def is_interpretable_support_content(
    customer_text: str,
    reply_text: str = "",
    ancestor_turns: Optional[List[Dict[str, Any]]] = None
) -> Tuple[bool, str]:
    """
    Validates that a candidate interaction contains interpretable support content.
    Evaluates target customer message and allowed prior ancestor context turns. Excludes future reply.
    """
    return is_contextually_interpretable(customer_text, ancestor_turns)



def normalize_inquiry_for_dedup(text: str) -> str:
    """
    Normalizes customer inquiry text for exact duplicate detection across conversation groups.
    Removes handles, URLs, punctuation, and excess whitespace.
    """
    t = text.lower()
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'@[a-z0-9_]+', '', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def compute_token_jaccard(text1: str, text2: str) -> float:
    """Computes Jaccard similarity between word tokens of two normalized texts."""
    tokens1 = set(text1.split())
    tokens2 = set(text2.split())
    if not tokens1 or not tokens2:
        return 0.0
    return len(tokens1 & tokens2) / len(tokens1 | tokens2)


def parse_tweet_timestamp(created_at_str: str) -> float:
    """Parses Twitter timestamp string to unix epoch seconds for stable sorting."""
    if not created_at_str:
        return 0.0
    try:
        dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        return dt.timestamp()
    except Exception:
        return 0.0


def candidate_turn_sort_key(item: Dict[str, Any]) -> Tuple[float, float, str, float, float, str]:
    """
    Deterministic sort key for candidate (customer, brand_reply) turns within a conversation group:
    1. Earliest customer timestamp
    2. Lowest customer tweet ID (numeric, then string)
    3. Earliest brand reply timestamp
    4. Lowest brand reply tweet ID (numeric, then string)
    """
    target_cust = item["target_customer_tweet"]
    brand_reply = item["brand_reply_tweet"]
    cust_ts = parse_tweet_timestamp(target_cust.get("created_at", ""))
    cust_id = str(target_cust["tweet_id"])
    cust_id_num = int(cust_id) if cust_id.isdigit() else float('inf')
    reply_ts = parse_tweet_timestamp(brand_reply.get("created_at", ""))
    reply_id = str(brand_reply["tweet_id"])
    reply_id_num = int(reply_id) if reply_id.isdigit() else float('inf')
    return (cust_ts, cust_id_num, cust_id, reply_ts, reply_id_num, reply_id)


def extract_phase2_candidates(
    cursor: sqlite3.Cursor,
    review_excluded_roots: Set[str],
    return_non_english: bool = False
) -> Any:
    """
    Extracts all candidate Spotify conversation groups from SQLite index.
    Filters candidate turns, traces ancestor trees, applies quality & language rules,
    and returns (valid_candidates, exclusion_counts, excluded_records_sample).
    """
    print("Querying SpotifyCares outbound replies to customer parent turns...", flush=True)

    cursor.execute("""
        SELECT 
            b.tweet_id AS brand_reply_tweet_id,
            b.author_id AS brand_author_id,
            b.created_at AS brand_created_at,
            b.text AS brand_text,
            b.in_response_to_tweet_id AS target_customer_tweet_id,
            p.author_id AS cust_author_id,
            p.inbound AS cust_inbound,
            p.created_at AS cust_created_at,
            p.text AS cust_text,
            p.in_response_to_tweet_id AS cust_parent_id
        FROM tweets b
        JOIN tweets p ON b.in_response_to_tweet_id = p.tweet_id
        WHERE b.author_id = 'SpotifyCares'
          AND b.inbound = 0
          AND p.inbound = 1
          AND p.author_id != 'SpotifyCares'
    """)
    rows = cursor.fetchall()
    print(f"  Found {len(rows):,} candidate (customer, brand_reply) pairs.", flush=True)

    exclusion_counts: Counter = Counter()
    uncertain_language_cases: List[Dict[str, Any]] = []
    non_english_cases: List[Dict[str, Any]] = []

    group_candidates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        b_reply_id = str(row["brand_reply_tweet_id"])
        target_cust_id = str(row["target_customer_tweet_id"])
        cust_tweet = fetch_tweet_by_id(cursor, target_cust_id)
        if not cust_tweet:
            exclusion_counts["MISSING_CUSTOMER_TWEET"] += 1
            continue

        b_tweet = fetch_tweet_by_id(cursor, b_reply_id)
        if not b_tweet:
            exclusion_counts["MISSING_BRAND_TWEET"] += 1
            continue

        root_tweet, root_complete, root_flags = find_root_tweet(cursor, cust_tweet)
        group_id = str(root_tweet["tweet_id"])

        group_candidates[group_id].append({
            "group_id": group_id,
            "root_tweet": root_tweet,
            "target_customer_tweet": cust_tweet,
            "brand_reply_tweet": b_tweet,
            "root_complete": root_complete,
            "root_flags": root_flags,
        })

    print(f"  Identified {len(group_candidates):,} unique conversation groups.", flush=True)

    # Sort groups deterministically by group ID so extraction order is independent of SQLite return order
    sorted_group_ids = sorted(
        group_candidates.keys(),
        key=lambda gid: (int(gid) if gid.isdigit() else float('inf'), str(gid))
    )

    valid_candidates: List[Dict[str, Any]] = []

    for group_id in sorted_group_ids:
        items = group_candidates[group_id]
        # Sort candidate turns deterministically: earliest customer timestamp, lowest cust tweet ID, earliest reply timestamp, lowest reply ID
        sorted_items = sorted(items, key=candidate_turn_sort_key)

        # Verify structural completeness of the root and conversation tree
        primary_item = sorted_items[0]
        root_tweet = primary_item["root_tweet"]
        thread_tweets, tree_complete, tree_flags = collect_thread_tree(cursor, root_tweet)
        all_structural_flags = list(set(primary_item["root_flags"] + tree_flags))
        is_structurally_complete = primary_item["root_complete"] and tree_complete and (len(all_structural_flags) == 0)

        if not is_structurally_complete:
            reason = all_structural_flags[0] if all_structural_flags else "STRUCTURALLY_INCOMPLETE"
            exclusion_counts[f"STRUCTURAL_{reason}"] += 1
            continue

        selected_candidate = None
        last_failure_reason = "NO_ELIGIBLE_CANDIDATE_TURNS"

        # Evaluate eligible customer turns within the conversation group before selecting one
        for item in sorted_items:
            target_cust = item["target_customer_tweet"]
            brand_reply = item["brand_reply_tweet"]

            # 1. Verify that the selected Spotify reply directly references the selected customer turn
            if str(brand_reply.get("in_response_to_tweet_id", "")) != str(target_cust["tweet_id"]):
                last_failure_reason = "REPLY_DOES_NOT_REFERENCE_CUSTOMER_TURN"
                continue

            # 2. Verify customer turn properties (must be inbound and not Spotify)
            if int(target_cust.get("inbound", 0)) != 1 or target_cust.get("author_id") == BRAND_NAME:
                last_failure_reason = "INVALID_CUSTOMER_TURN"
                continue

            # 3. Build ancestor path strictly up to the target customer inquiry
            try:
                ancestor_path = build_ancestor_path(
                    thread_tweets,
                    target_tweet_id=str(target_cust["tweet_id"]),
                    brand_name=BRAND_NAME
                )
            except Exception:
                last_failure_reason = "ANCESTOR_PATH_ERROR"
                continue

            # 4. Evaluate language on target customer message and allowed prior ancestor context
            target_text = target_cust.get("text", "")
            prior_context_turns = ancestor_path[:-1] if len(ancestor_path) > 1 else []

            lang_state, lang_score, lang_reason = detect_language_state(
                target_text,
                ancestor_turns=prior_context_turns
            )

            if lang_state == LANGUAGE_STATE_UNCERTAIN:
                redacted_target = redact_sensitive_info(target_text)
                uncertain_language_cases.append({
                    "sample_category": "uncertain",
                    "group_id": group_id,
                    "target_customer_tweet_id": str(target_cust["tweet_id"]),
                    "text_snippet": redacted_target[:100],
                    "customer_text": redacted_target,
                    "ancestor_turns": [
                        {
                            "tweet_id": str(t["tweet_id"]),
                            "author_id": BRAND_NAME if (not t.get("inbound") or str(t.get("author_id", "")).lower() == "spotifycares") else "Customer",
                            "inbound": int(t.get("inbound", 0)),
                            "created_at": t.get("created_at", ""),
                            "text": redact_sensitive_info(t.get("text", ""))
                        }
                        for t in ancestor_path
                    ],
                    "language_state": lang_state,
                    "language_heuristic_score": lang_score,
                    "detection_reason": lang_reason,
                    "inclusion_decision": "excluded_pending_human_review",
                })
                last_failure_reason = f"UNCERTAIN_LANGUAGE_{lang_reason}"
                continue

            if lang_state == LANGUAGE_STATE_NON_ENGLISH:
                redacted_target = redact_sensitive_info(target_text)
                non_english_cases.append({
                    "sample_category": "rejected",
                    "group_id": group_id,
                    "target_customer_tweet_id": str(target_cust["tweet_id"]),
                    "text_snippet": redacted_target[:100],
                    "customer_text": redacted_target,
                    "ancestor_turns": [
                        {
                            "tweet_id": str(t["tweet_id"]),
                            "author_id": BRAND_NAME if (not t.get("inbound") or str(t.get("author_id", "")).lower() == "spotifycares") else "Customer",
                            "inbound": int(t.get("inbound", 0)),
                            "created_at": t.get("created_at", ""),
                            "text": redact_sensitive_info(t.get("text", ""))
                        }
                        for t in ancestor_path
                    ],
                    "language_state": lang_state,
                    "language_heuristic_score": lang_score,
                    "detection_reason": lang_reason,
                    "inclusion_decision": "excluded_non_english",
                })
                last_failure_reason = f"NON_ENGLISH_{lang_reason}"
                continue

            # 5. Evaluate interpretable support content (strictly target and prior context, never future reply)
            interpretable, interp_reason = is_contextually_interpretable(
                target_text,
                ancestor_turns=prior_context_turns
            )
            if not interpretable:
                last_failure_reason = f"UNINTERPRETABLE_{interp_reason}"
                continue

            # Eligible customer turn found! Select it and stop searching other turns in this group
            model_ctx = build_model_context(
                ancestor_path,
                target_tweet_id=str(target_cust["tweet_id"]),
                brand_name=BRAND_NAME
            )

            actor_map = model_ctx.get("actor_map", {})
            prepared_ancestor_turns = [
                {
                    "tweet_id": str(t["tweet_id"]),
                    "author_id": BRAND_NAME if (not t.get("inbound") or str(t.get("author_id", "")).lower() == "spotifycares") else actor_map.get(t.get("author_id"), "Customer_1"),
                    "inbound": int(t.get("inbound", 0)),
                    "created_at": t.get("created_at", ""),
                    "text": redact_sensitive_info(t.get("text", "")),
                    "in_response_to_tweet_id": str(t.get("in_response_to_tweet_id")) if t.get("in_response_to_tweet_id") is not None and str(t.get("in_response_to_tweet_id")).strip() not in ("", "None", "nan") else None
                }
                for t in ancestor_path
            ]

            # Compute input_quality_flags strictly from prepared ancestor turns (no future-reply leakage)
            input_quality_flags = detect_quality_and_structural_flags(prepared_ancestor_turns)

            redacted_cust_text = redact_sensitive_info(target_cust.get("text", ""))
            redacted_reply_text = redact_sensitive_info(brand_reply.get("text", ""))

            # Compute reply-derived flags separately for reference metadata
            reply_quality_flags = detect_quality_and_structural_flags([{
                "tweet_id": str(brand_reply["tweet_id"]),
                "author_id": BRAND_NAME,
                "inbound": 0,
                "created_at": brand_reply.get("created_at", ""),
                "text": redacted_reply_text,
                "in_response_to_tweet_id": str(target_cust["tweet_id"])
            }])

            norm_inquiry = normalize_inquiry_for_dedup(redacted_cust_text)
            is_review_group = (group_id in review_excluded_roots)
            example_id = f"{BRAND_NAME}:{group_id}:{target_cust['tweet_id']}:{brand_reply['tweet_id']}"

            selected_candidate = {
                "example_id": example_id,
                "group_id": group_id,
                "target_customer_tweet_id": str(target_cust["tweet_id"]),
                "selected_brand_reply_tweet_id": str(brand_reply["tweet_id"]),
                "customer_text": redacted_cust_text,
                "brand_reply_text": redacted_reply_text,
                "raw_customer_text": target_cust.get("text", ""),
                "raw_brand_reply_text": brand_reply.get("text", ""),
                "normalized_inquiry": norm_inquiry,
                "model_input_text": model_ctx["model_input_text"],
                "actor_map": actor_map,
                "ancestor_turns": prepared_ancestor_turns,
                "input_quality_flags": input_quality_flags,
                "reply_quality_flags": reply_quality_flags,
                "quality_flags": input_quality_flags,  # Input-only flags for routing/challenge/inference
                "created_at": target_cust.get("created_at", ""),
                "is_review_group": is_review_group,
                "thread_turn_count": len(thread_tweets),
                "language_state": lang_state,
                "language_heuristic_score": lang_score,
                "language_detection_reason": lang_reason,
            }
            break

        if selected_candidate is not None:
            valid_candidates.append(selected_candidate)
        else:
            exclusion_counts[last_failure_reason] += 1

    print(f"  Valid eligible candidates after quality/language filters: {len(valid_candidates):,}.", flush=True)
    if return_non_english:
        return valid_candidates, dict(exclusion_counts), uncertain_language_cases, non_english_cases
    return valid_candidates, dict(exclusion_counts), uncertain_language_cases



def deduplicate_and_audit_leakage(
    candidates: List[Dict[str, Any]],
    restricted_root_ids: Optional[Set[str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], int]:
    """
    Detects exact and near-duplicate customer inquiries across conversation groups
    using an inverted index with prefix and length filtering over the full population.
    Builds deterministic transitive duplicate clusters and propagates review/dev restrictions.
    Returns (deduplicated_candidates, leakage_report, exact_dup_count).
    """
    print("Auditing exact and near-duplicate inquiries across groups using inverted index...", flush=True)

    if restricted_root_ids is None:
        restricted_root_ids = set()

    # Find all duplicate pairs across full candidate population
    duplicate_pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.85)

    # Build transitive clusters
    clusters = build_transitive_clusters(candidates, duplicate_pairs)

    # Gather restricted roots from candidate flags + explicit restricted_root_ids
    all_restricted = set(restricted_root_ids)
    for c in candidates:
        if c.get("is_review_group"):
            all_restricted.add(str(c["group_id"]))

    updated_clusters = propagate_restrictions_to_clusters(clusters, all_restricted)

    # Retain canonical representative for each cluster
    candidates_by_gid = {str(c["group_id"]): c for c in candidates}
    deduplicated_candidates: List[Dict[str, Any]] = []
    exact_duplicates_removed = 0
    near_duplicates_removed = 0
    exact_duplicate_clusters = []
    near_duplicate_clusters = []

    # Map every group_id in the candidate universe to its cluster membership details
    group_membership: Dict[str, Dict[str, Any]] = {}
    for cluster in updated_clusters:
        cid = cluster["cluster_id"]
        can_gid = cluster["canonical_group_id"]
        is_restricted = cluster["ineligible_for_eval"]
        for gid in cluster["member_group_ids"]:
            group_membership[gid] = {
                "group_id": gid,
                "cluster_id": cid,
                "canonical_group_id": can_gid,
                "is_canonical": (gid == can_gid),
                "removed_as_duplicate": (gid != can_gid),
                "ineligible_for_eval": is_restricted,
                "restricted_members": cluster["restricted_members"]
            }

    cluster_membership_manifest = {
        "total_clusters": len(updated_clusters),
        "total_groups": len(candidates),
        "singleton_clusters_count": sum(1 for c in updated_clusters if c["size"] == 1),
        "duplicate_clusters_count": sum(1 for c in updated_clusters if c["size"] > 1),
        "restricted_clusters_count": sum(1 for c in updated_clusters if c["ineligible_for_eval"]),
        "clusters": updated_clusters,
        "group_membership": group_membership,
    }

    for cluster in updated_clusters:
        canonical_gid = cluster["canonical_group_id"]
        canonical_candidate = dict(candidates_by_gid[canonical_gid])
        canonical_candidate["duplicate_cluster_id"] = cluster["cluster_id"]

        # Propagate evaluation restriction to the retained representative
        if cluster["ineligible_for_eval"]:
            canonical_candidate["is_review_group"] = True

        deduplicated_candidates.append(canonical_candidate)

        if cluster["size"] > 1:
            # Check if all internal edges are exact (similarity == 1.0)
            is_pure_exact = all(
                edge["similarity"] == 1.0 for edge in cluster["internal_edges"]
            ) if cluster["internal_edges"] else False

            raw_inq = canonical_candidate.get("customer_text") or canonical_candidate.get("raw_customer_text") or ""
            redacted_inquiry = redact_sensitive_info(raw_inq)
            inquiry_snippet = redacted_inquiry[:100]
            norm_text = canonical_candidate.get("normalized_inquiry", "")[:100]
            cluster_info = {
                "cluster_id": cluster["cluster_id"],
                "inquiry_snippet": inquiry_snippet,
                "normalized_inquiry": norm_text,
                "cluster_size": cluster["size"],
                "canonical_group_id": canonical_gid,
                "duplicate_group_ids": [gid for gid in cluster["member_group_ids"] if gid != canonical_gid],
                "ineligible_for_eval": cluster["ineligible_for_eval"],
                "restricted_members": cluster["restricted_members"],
            }

            if is_pure_exact:
                exact_duplicates_removed += (cluster["size"] - 1)
                exact_duplicate_clusters.append(cluster_info)
            else:
                near_duplicates_removed += (cluster["size"] - 1)
                near_duplicate_clusters.append(cluster_info)

    total_duplicates_removed = exact_duplicates_removed + near_duplicates_removed
    print(f"  Removed {total_duplicates_removed} duplicates ({exact_duplicates_removed} exact, {near_duplicates_removed} near) across {len(exact_duplicate_clusters) + len(near_duplicate_clusters)} clusters.", flush=True)

    near_pairs_sample = [
        {
            "group_1": p[0],
            "group_2": p[1],
            "similarity": p[2],
            "match_type": p[3]
        }
        for p in duplicate_pairs if p[3] == "near"
    ][:20]

    leakage_audit = {
        "matching_rule": {
            "exact_duplicate_rule": "Normalized inquiry text matching after lowercase, punctuation removal, URL stripping, and whitespace collapse.",
            "near_duplicate_rule": "Token Jaccard similarity >= 0.85 evaluated via inverted index with prefix and length filtering on the full candidate population."
        },
        "exact_duplicates_removed": exact_duplicates_removed,
        "near_duplicates_removed": near_duplicates_removed,
        "total_duplicates_removed": total_duplicates_removed,
        "exact_duplicate_clusters_count": len(exact_duplicate_clusters),
        "near_duplicate_clusters_count": len(near_duplicate_clusters),
        "total_duplicate_clusters_count": len(exact_duplicate_clusters) + len(near_duplicate_clusters),
        "exact_duplicate_clusters_sample": exact_duplicate_clusters[:20],
        "near_duplicate_pairs_detected": len(duplicate_pairs),
        "near_duplicate_sample": near_pairs_sample,
        "restricted_clusters_propagated": sum(1 for c in updated_clusters if c["ineligible_for_eval"] and c["size"] > 1),
        "cluster_membership": cluster_membership_manifest
    }

    return deduplicated_candidates, leakage_audit, exact_duplicates_removed



def create_partitions(
    candidates: List[Dict[str, Any]],
    target_historical: int = TARGET_HISTORICAL,
    target_dev: int = TARGET_DEV,
    target_eval_pool: int = TARGET_EVAL_POOL,
    seed: int = RANDOM_SEED
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Deterministically partitions eligible candidates into:
    - dev (50 groups, strictly non-review)
    - eval_pool (up to 1,000 groups, strictly non-review)
    - historical (target 3,000 groups)
    """
    print(f"Partitioning eligible candidates with seed {seed}...", flush=True)

    candidates.sort(key=lambda x: (
        int(x["group_id"]) if x["group_id"].isdigit() else x["group_id"],
        int(x["target_customer_tweet_id"]) if x["target_customer_tweet_id"].isdigit() else x["target_customer_tweet_id"]
    ))

    rng = random.Random(seed)
    rng.shuffle(candidates)

    non_review_candidates = [c for c in candidates if not c["is_review_group"]]
    review_candidates = [c for c in candidates if c["is_review_group"]]

    print(f"  Non-review eligible candidates available: {len(non_review_candidates):,}")
    print(f"  Review candidates (excluded from eval_pool): {len(review_candidates):,}")

    dev_set = non_review_candidates[:target_dev]
    remaining_non_review = non_review_candidates[target_dev:]

    eval_pool = remaining_non_review[:target_eval_pool]
    unused_non_review = remaining_non_review[target_eval_pool:]

    historical_pool = unused_non_review + review_candidates
    historical_corpus = historical_pool[:target_historical]

    print(f"  Allocated Partitions:")
    print(f"    - Dev Inputs     : {len(dev_set):,} groups")
    print(f"    - Eval Pool      : {len(eval_pool):,} groups")
    print(f"    - Historical KB  : {len(historical_corpus):,} groups")

    all_partitioned: List[Dict[str, Any]] = []
    for item in dev_set:
        all_partitioned.append({**item, "partition": "dev"})
    for item in eval_pool:
        all_partitioned.append({**item, "partition": "eval_pool"})
    for item in historical_corpus:
        all_partitioned.append({**item, "partition": "historical"})

    return dev_set, eval_pool, historical_corpus, all_partitioned


def export_phase2_outputs(
    dev_set: List[Dict[str, Any]],
    eval_pool: List[Dict[str, Any]],
    historical_corpus: List[Dict[str, Any]],
    all_partitioned: List[Dict[str, Any]],
    exclusion_summary: Dict[str, Any],
    leakage_report: Dict[str, Any],
    source_checksum: str,
    uncertain_language_cases: Optional[List[Dict[str, Any]]] = None,
    sample_review_records: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Exports all Phase 2 files in the specified paths with strict schemas."""
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def _anonymize_and_redact_turns(turns: List[Dict[str, Any]], actor_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        anon = []
        actor_map = actor_map or {}
        for t in turns:
            raw_author = str(t.get("author_id", ""))
            is_inb = bool(t.get("inbound", 0))
            if not is_inb or raw_author.lower() == BRAND_NAME.lower():
                author_id = BRAND_NAME
            else:
                author_id = actor_map.get(raw_author, raw_author if raw_author.startswith("Customer_") else "Customer_1")

            parent_id = t.get("in_response_to_tweet_id")
            clean_parent = str(parent_id).strip() if parent_id is not None and str(parent_id).strip() not in ("", "None", "nan") else None

            anon.append({
                "tweet_id": str(t.get("tweet_id", "")),
                "author_id": author_id,
                "inbound": int(t.get("inbound", 0)),
                "created_at": t.get("created_at", ""),
                "text": redact_sensitive_info(t.get("text", "")),
                "in_response_to_tweet_id": clean_parent,
            })
        return anon

    # 1. Historical Knowledge Corpus
    historical_path = OUTPUT_DATA_DIR / "spotify_knowledge.jsonl"
    with open(historical_path, "w", encoding="utf-8") as f:
        for item in historical_corpus:
            rec = {
                "example_id": item["example_id"],
                "group_id": item["group_id"],
                "target_customer_tweet_id": item["target_customer_tweet_id"],
                "selected_brand_reply_tweet_id": item["selected_brand_reply_tweet_id"],
                "customer_text": redact_sensitive_info(item["customer_text"]),
                "brand_reply_text": redact_sensitive_info(item["brand_reply_text"]),
                "ancestor_turns": _anonymize_and_redact_turns(item.get("ancestor_turns", []), item.get("actor_map", {})),
                "input_quality_flags": item["input_quality_flags"],
                "reply_quality_flags": item["reply_quality_flags"],
                "quality_flags": item["input_quality_flags"],
                "source_csv_sha256": source_checksum,
                "created_at": item["created_at"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(historical_corpus)} records to {_safe_relpath(historical_path)}")

    # 2. Development Inputs (no brand reply, input-only flags, strictly no raw identity mappings)
    dev_path = OUTPUT_DATA_DIR / "dev_inputs.jsonl"
    with open(dev_path, "w", encoding="utf-8") as f:
        for item in dev_set:
            rec = {
                "example_id": item["example_id"],
                "group_id": item["group_id"],
                "target_customer_tweet_id": item["target_customer_tweet_id"],
                "selected_brand_reply_tweet_id": item["selected_brand_reply_tweet_id"],
                "model_input_text": item["model_input_text"],
                "ancestor_turns": _anonymize_and_redact_turns(item.get("ancestor_turns", []), item.get("actor_map", {})),
                "input_quality_flags": item["input_quality_flags"],
                "quality_flags": item["input_quality_flags"],
                "source_csv_sha256": source_checksum,
                "created_at": item["created_at"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(dev_set)} records to {_safe_relpath(dev_path)}")

    # 3. Evaluation Pool Inputs (no brand reply, input-only flags, strictly no raw identity mappings)
    eval_path = OUTPUT_DATA_DIR / "eval_pool_inputs.jsonl"
    with open(eval_path, "w", encoding="utf-8") as f:
        for item in eval_pool:
            rec = {
                "example_id": item["example_id"],
                "group_id": item["group_id"],
                "target_customer_tweet_id": item["target_customer_tweet_id"],
                "selected_brand_reply_tweet_id": item["selected_brand_reply_tweet_id"],
                "model_input_text": item["model_input_text"],
                "ancestor_turns": _anonymize_and_redact_turns(item.get("ancestor_turns", []), item.get("actor_map", {})),
                "input_quality_flags": item["input_quality_flags"],
                "quality_flags": item["input_quality_flags"],
                "source_csv_sha256": source_checksum,
                "created_at": item["created_at"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(eval_pool)} records to {_safe_relpath(eval_path)}")

    # 4. Split Manifest
    manifest_path = OUTPUT_MANIFEST_DIR / "split_manifest.jsonl"
    with open(manifest_path, "w", encoding="utf-8") as f:
        for item in all_partitioned:
            rec = {
                "example_id": item["example_id"],
                "group_id": item["group_id"],
                "target_customer_tweet_id": item["target_customer_tweet_id"],
                "selected_brand_reply_tweet_id": item["selected_brand_reply_tweet_id"],
                "partition": item["partition"],
                "duplicate_cluster_id": item.get("duplicate_cluster_id", f"cluster_{item['group_id']}"),
                "source_csv_sha256": source_checksum,
                "seed": RANDOM_SEED,
                "preprocessing_version": PREPROCESSING_VERSION,
                "input_quality_flags": item["input_quality_flags"],
                "reply_quality_flags": item["reply_quality_flags"],
                "quality_flags": item["input_quality_flags"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(all_partitioned)} manifest records to {_safe_relpath(manifest_path)}")

    # 5. Cluster Membership Manifest
    cluster_membership = leakage_report.get("cluster_membership")
    if cluster_membership:
        cluster_manifest_path = OUTPUT_MANIFEST_DIR / "cluster_membership.json"
        with open(cluster_manifest_path, "w", encoding="utf-8") as f:
            json.dump(cluster_membership, f, indent=2, ensure_ascii=False)
        print(f"Wrote cluster membership manifest to {_safe_relpath(cluster_manifest_path)}")

        cluster_report_path = OUTPUT_REPORT_DIR / "cluster_membership.json"
        with open(cluster_report_path, "w", encoding="utf-8") as f:
            json.dump(cluster_membership, f, indent=2, ensure_ascii=False)
        print(f"Wrote cluster membership report to {_safe_relpath(cluster_report_path)}")

    # 6. Exclusion Summary JSON
    exclusion_path = OUTPUT_REPORT_DIR / "exclusion_summary.json"
    with open(exclusion_path, "w", encoding="utf-8") as f:
        json.dump(exclusion_summary, f, indent=2, ensure_ascii=False)
    print(f"Wrote exclusion summary to {_safe_relpath(exclusion_path)}")

    # 7. Leakage Report JSON
    leakage_path = OUTPUT_REPORT_DIR / "leakage_report.json"
    with open(leakage_path, "w", encoding="utf-8") as f:
        json.dump(leakage_report, f, indent=2, ensure_ascii=False)
    print(f"Wrote leakage report to {_safe_relpath(leakage_path)}")

    # 8. Dev Preview Markdown (20 examples)
    preview_md_path = OUTPUT_REPORT_DIR / "dev_preview.md"
    generate_dev_preview_md(dev_set[:20], preview_md_path)
    print(f"Wrote dev preview to {_safe_relpath(preview_md_path)}")

    # 9. Language Review Queue JSON
    if uncertain_language_cases is not None:
        queue_path = OUTPUT_REPORT_DIR / "language_review_queue.json"
        queue_payload = {
            "status": "pending_human_review",
            "policy": "Uncertain language cases are placed in this review queue and excluded from English-only splits pending human verification.",
            "total_uncertain_cases": len(uncertain_language_cases),
            "cases": uncertain_language_cases,
        }
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_payload, f, indent=2, ensure_ascii=False)
        print(f"Wrote language review queue ({len(uncertain_language_cases)} cases) to {_safe_relpath(queue_path)}")

    # 10. Language Human Review Sheet CSV
    if sample_review_records:
        sheet_path = OUTPUT_REPORT_DIR / "language_human_review_sheet.csv"
        export_human_review_sheet(sample_review_records, sheet_path)
        print(f"Wrote human review sheet ({len(sample_review_records)} cases) to {_safe_relpath(sheet_path)}")


def audit_exported_dataset_on_disk(
    data_dir: Path = OUTPUT_DATA_DIR,
    manifest_dir: Path = OUTPUT_MANIFEST_DIR,
    report_dir: Path = OUTPUT_REPORT_DIR,
    review_excluded_roots: Optional[Set[str]] = None,
    expected_source_csv_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Independently inspects exported files on disk to verify all integrity and isolation invariants.
    Fails immediately with ValueError on any violation.
    """
    if review_excluded_roots is None:
        review_excluded_roots = set()

    manifest_path = manifest_dir / "split_manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest missing: {manifest_path}")

    # 1. Read manifest entries
    manifest_entries: List[Dict[str, Any]] = []
    manifest_by_example_id: Dict[str, Dict[str, Any]] = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            entry = json.loads(line)
            eid = entry.get("example_id")
            if not eid:
                raise ValueError(f"Missing example_id at line {line_num} of {manifest_path}")
            if eid in manifest_by_example_id:
                raise ValueError(f"Duplicate example_id in manifest: {eid}")
            manifest_by_example_id[eid] = entry
            manifest_entries.append(entry)

    # Check source_csv_sha256 in manifest
    if expected_source_csv_sha256:
        for entry in manifest_entries:
            if entry.get("source_csv_sha256") != expected_source_csv_sha256:
                raise ValueError(
                    f"Manifest entry {entry['example_id']} has mismatched source_csv_sha256: "
                    f"{entry.get('source_csv_sha256')} != {expected_source_csv_sha256}"
                )

    # 2. Read exported data partitions from disk
    historical_path = data_dir / "spotify_knowledge.jsonl"
    dev_path = data_dir / "dev_inputs.jsonl"
    eval_path = data_dir / "eval_pool_inputs.jsonl"

    exported_records: Dict[str, List[Dict[str, Any]]] = {
        "historical": [],
        "dev": [],
        "eval_pool": []
    }

    for part_name, fpath in [("historical", historical_path), ("dev", dev_path), ("eval_pool", eval_path)]:
        if not fpath.exists():
            raise FileNotFoundError(f"Exported partition missing: {fpath}")
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    exported_records[part_name].append(json.loads(line))

    # Auditor Check 1: Every exported example matches exactly one manifest entry
    seen_example_ids: Set[str] = set()
    for part_name, records in exported_records.items():
        for rec in records:
            eid = rec["example_id"]
            if eid in seen_example_ids:
                raise ValueError(f"Duplicate exported example_id across files: {eid}")
            seen_example_ids.add(eid)
            if eid not in manifest_by_example_id:
                raise ValueError(f"Exported example {eid} not found in split manifest!")
            man_entry = manifest_by_example_id[eid]
            if man_entry["partition"] != part_name:
                raise ValueError(
                    f"Partition mismatch for {eid}: file has {part_name}, manifest has {man_entry['partition']}"
                )

    active_manifest_entries = [
        m for m in manifest_entries if m.get("partition") in ("historical", "dev", "eval_pool")
    ]
    if len(seen_example_ids) != len(active_manifest_entries):
        raise ValueError(
            f"Count mismatch: {len(seen_example_ids)} exported records vs {len(active_manifest_entries)} active manifest entries."
        )

    # Auditor Check 2: Every selected group has a recorded cluster
    cluster_manifest_path = report_dir / "cluster_membership.json"
    if not cluster_manifest_path.exists():
        cluster_manifest_path = manifest_dir / "cluster_membership.json"
    if not cluster_manifest_path.exists():
        raise FileNotFoundError("Cluster membership manifest missing from disk.")

    with open(cluster_manifest_path, "r", encoding="utf-8") as f:
        cluster_manifest = json.load(f)
    group_membership = cluster_manifest.get("group_membership", {})

    for entry in manifest_entries:
        cid = entry.get("duplicate_cluster_id")
        if not cid:
            raise ValueError(f"Manifest entry {entry['example_id']} has no duplicate_cluster_id recorded!")
        gid = str(entry["group_id"])
        if gid not in group_membership:
            raise ValueError(f"Selected group {gid} not recorded in cluster membership manifest!")
        if group_membership[gid]["cluster_id"] != cid:
            raise ValueError(
                f"Cluster ID mismatch for group {gid}: manifest={cid}, cluster_membership={group_membership[gid]['cluster_id']}"
            )

    # Auditor Check 3: Groups and clusters remain isolated across partitions
    part_groups: Dict[str, Set[str]] = defaultdict(set)
    part_clusters: Dict[str, Set[str]] = defaultdict(set)
    for entry in manifest_entries:
        part = entry["partition"]
        part_groups[part].add(str(entry["group_id"]))
        part_clusters[part].add(str(entry["duplicate_cluster_id"]))

    dev_eval_overlap = len(part_groups["dev"] & part_groups["eval_pool"])
    dev_hist_overlap = len(part_groups["dev"] & part_groups["historical"])
    eval_hist_overlap = len(part_groups["eval_pool"] & part_groups["historical"])

    cluster_dev_eval_overlap = len(part_clusters["dev"] & part_clusters["eval_pool"])
    cluster_dev_hist_overlap = len(part_clusters["dev"] & part_clusters["historical"])
    cluster_eval_hist_overlap = len(part_clusters["eval_pool"] & part_clusters["historical"])

    if dev_eval_overlap > 0 or dev_hist_overlap > 0 or eval_hist_overlap > 0:
        raise ValueError(
            f"Group isolation violation! dev_eval={dev_eval_overlap}, dev_hist={dev_hist_overlap}, eval_hist={eval_hist_overlap}"
        )
    if cluster_dev_eval_overlap > 0 or cluster_dev_hist_overlap > 0 or cluster_eval_hist_overlap > 0:
        raise ValueError(
            f"Cluster isolation violation! dev_eval={cluster_dev_eval_overlap}, dev_hist={cluster_dev_hist_overlap}, eval_hist={cluster_eval_hist_overlap}"
        )

    # Auditor Check 4: Review/development restrictions propagate through full cluster (including removed duplicates)
    review_eval_overlap = len(part_groups["eval_pool"] & review_excluded_roots)
    if review_eval_overlap > 0:
        raise ValueError(f"Review contamination: {review_eval_overlap} review groups found in eval_pool!")

    for cluster in cluster_manifest.get("clusters", []):
        if cluster.get("ineligible_for_eval"):
            # Ensure none of its members are in eval_pool
            for gid in cluster.get("member_group_ids", []):
                if gid in part_groups["eval_pool"]:
                    raise ValueError(
                        f"Cluster {cluster['cluster_id']} contains restricted member {gid} but was assigned to eval_pool!"
                    )

    # Check that development groups and their cluster members do not enter eval_pool
    dev_cluster_ids = part_clusters["dev"]
    for cid in dev_cluster_ids:
        if cid in part_clusters["eval_pool"]:
            raise ValueError(f"Cluster {cid} spans dev and eval_pool!")

    # Auditor Check 5: Target turns are customers and selected future replies are absent from context
    for part_name, records in exported_records.items():
        for rec in records:
            ancestor_turns = rec.get("ancestor_turns", [])
            if not ancestor_turns:
                raise ValueError(f"Empty ancestor_turns in {rec['example_id']}")
            target_turn = ancestor_turns[-1]
            if str(target_turn.get("tweet_id")) != str(rec["target_customer_tweet_id"]):
                raise ValueError(
                    f"Target tweet mismatch in {rec['example_id']}: last turn is {target_turn.get('tweet_id')}, expected {rec['target_customer_tweet_id']}"
                )
            if int(target_turn.get("inbound", 0)) != 1 or str(target_turn.get("author_id", "")).lower() == "spotifycares":
                raise ValueError(f"Target turn is not customer in {rec['example_id']}")

            reply_id = str(rec["selected_brand_reply_tweet_id"])
            ancestor_ids = {str(t.get("tweet_id")) for t in ancestor_turns}
            if reply_id in ancestor_ids:
                raise ValueError(f"Selected future reply {reply_id} leaked into ancestor_turns in {rec['example_id']}!")

            if "model_input_text" in rec and "brand_reply_text" in rec:
                reply_text = rec["brand_reply_text"].strip()
                if reply_text and len(reply_text) > 10 and reply_text in rec["model_input_text"]:
                    raise ValueError(f"Selected brand reply text leaked into model_input_text in {rec['example_id']}!")

    # Auditor Check 6: Input flags can be reproduced from allowed context alone
    for part_name, records in exported_records.items():
        for rec in records:
            recomputed = detect_quality_and_structural_flags(rec["ancestor_turns"])
            for flag_key in ["has_url", "private_handoff", "external_context_required", "suspected_multipart", "partial_text"]:
                if recomputed.get(flag_key) != rec["input_quality_flags"].get(flag_key):
                    raise ValueError(
                        f"Input flag reproduction mismatch for {flag_key} in {rec['example_id']}: "
                        f"recomputed={recomputed.get(flag_key)}, recorded={rec['input_quality_flags'].get(flag_key)}"
                    )

    # Check language review queue count directly from file
    queue_path = report_dir / "language_review_queue.json"
    actual_queue_count = 0
    if queue_path.exists():
        with open(queue_path, "r", encoding="utf-8") as f:
            q_data = json.load(f)
            actual_queue_count = len(q_data.get("cases", []))

    return {
        "manifest_records_count": len(manifest_entries),
        "historical_count": len(exported_records["historical"]),
        "dev_count": len(exported_records["dev"]),
        "eval_count": len(exported_records["eval_pool"]),
        "total_partitioned_groups": len(manifest_entries),
        "target_historical": TARGET_HISTORICAL,
        "target_dev": TARGET_DEV,
        "target_eval_pool": TARGET_EVAL_POOL,
        "historical_shortfall": max(0, TARGET_HISTORICAL - len(exported_records["historical"])),
        "dev_shortfall": max(0, TARGET_DEV - len(exported_records["dev"])),
        "eval_shortfall": max(0, TARGET_EVAL_POOL - len(exported_records["eval_pool"])),
        "dev_eval_overlap": dev_eval_overlap,
        "dev_hist_overlap": dev_hist_overlap,
        "eval_hist_overlap": eval_hist_overlap,
        "review_eval_overlap": review_eval_overlap,
        "cluster_dev_eval_overlap": cluster_dev_eval_overlap,
        "cluster_dev_hist_overlap": cluster_dev_hist_overlap,
        "cluster_eval_hist_overlap": cluster_eval_hist_overlap,
        "actual_language_review_queue_count": actual_queue_count,
        "auditor_checks_passed": True,
    }


def generate_data_summary_md(
    dev_set: List[Dict[str, Any]],
    eval_pool: List[Dict[str, Any]],
    historical_corpus: List[Dict[str, Any]],
    exclusion_summary: Dict[str, Any],
    leakage_report: Dict[str, Any],
    audit_results: Dict[str, Any],
    output_path: Path
) -> None:
    """Generates a concise markdown summary of dataset counts, flags, and leakage audit using measured disk values."""
    all_items = dev_set + eval_pool + historical_corpus

    input_flag_counts = {
        "has_url": sum(1 for x in all_items if x["input_quality_flags"].get("has_url")),
        "private_handoff": sum(1 for x in all_items if x["input_quality_flags"].get("private_handoff")),
        "external_context_required": sum(1 for x in all_items if x["input_quality_flags"].get("external_context_required")),
        "suspected_multipart": sum(1 for x in all_items if x["input_quality_flags"].get("suspected_multipart")),
        "partial_text": sum(1 for x in all_items if x["input_quality_flags"].get("partial_text")),
    }
    reply_flag_counts = {
        "has_url": sum(1 for x in all_items if x["reply_quality_flags"].get("has_url")),
        "private_handoff": sum(1 for x in all_items if x["reply_quality_flags"].get("private_handoff")),
        "external_context_required": sum(1 for x in all_items if x["reply_quality_flags"].get("external_context_required")),
        "suspected_multipart": sum(1 for x in all_items if x["reply_quality_flags"].get("suspected_multipart")),
        "partial_text": sum(1 for x in all_items if x["reply_quality_flags"].get("partial_text")),
    }

    lang_counts = exclusion_summary.get("language_state_counts", {})
    decision_counts = exclusion_summary.get("inclusion_decision_counts", {})

    content = f"""# Phase 2 Data Summary: Spotify Historical Corpus & Evaluation Pool (v2)

## Partition Sizes & Shortfalls (Measured On Disk)
- **Historical Corpus (`spotify_knowledge.jsonl`)**: {audit_results['historical_count']:,} groups (target: {audit_results['target_historical']:,}, shortfall: {audit_results['historical_shortfall']:,})
- **Development Inputs (`dev_inputs.jsonl`)**: {audit_results['dev_count']:,} messages (target: {audit_results['target_dev']:,}, shortfall: {audit_results['dev_shortfall']:,})
- **Evaluation Pool Inputs (`eval_pool_inputs.jsonl`)**: {audit_results['eval_count']:,} groups (target: {audit_results['target_eval_pool']:,}, shortfall: {audit_results['eval_shortfall']:,})
- **Total Partitioned Groups**: {audit_results['total_partitioned_groups']:,} distinct conversation groups

## Split Isolation & Leakage Audit (Measured Disk Overlaps)
- **Dev ↔ Eval Group Overlap**: {audit_results['dev_eval_overlap']}
- **Dev ↔ Historical Group Overlap**: {audit_results['dev_hist_overlap']}
- **Eval ↔ Historical Group Overlap**: {audit_results['eval_hist_overlap']}
- **Review Exclusions ↔ Eval Pool Overlap**: {audit_results['review_eval_overlap']}
- **Dev ↔ Eval Cluster Overlap**: {audit_results['cluster_dev_eval_overlap']}
- **Dev ↔ Historical Cluster Overlap**: {audit_results['cluster_dev_hist_overlap']}
- **Eval ↔ Historical Cluster Overlap**: {audit_results['cluster_eval_hist_overlap']}
- **Exact Duplicate Inquiries Deduplicated**: {leakage_report.get('exact_duplicates_removed', 0):,} groups removed across {leakage_report.get('exact_duplicate_clusters_count', 0):,} clusters.
- **Review Group Blacklist**: All {exclusion_summary.get('review_groups_blacklisted_from_eval', 0)} previously reviewed groups excluded from `eval_pool`.
- **Model Input Leakage Prevention**: In both `dev_inputs.jsonl` and `eval_pool_inputs.jsonl`, the selected brand reply is verified absent from inputs.
- **Input Quality Flags**: Verified reproducible from allowed customer ancestor context alone.

## Language Detection & Contextual Interpretability
- **Three Explicit Language States**: `english`, `non_english`, `uncertain`
- **Scoring**: Rule-based score named `language_heuristic_score` (not presented as calibrated confidence).
- **Language State Distribution**:
  - `english`: {lang_counts.get('english', len(all_items)):,}
  - `non_english`: {lang_counts.get('non_english', 0):,}
  - `uncertain`: {lang_counts.get('uncertain', 0):,}
- **Inclusion Decision Breakdown**:
  - `included_english_eligible`: {decision_counts.get('included_english_eligible', len(all_items)):,}
  - `excluded_uncertain_pending_review`: {decision_counts.get('excluded_uncertain_pending_review', 0):,}
  - `excluded_non_english`: {decision_counts.get('excluded_non_english', 0):,}
  - `excluded_uninterpretable`: {decision_counts.get('excluded_uninterpretable', 0):,}
  - `excluded_structural_or_reference`: {decision_counts.get('excluded_structural_or_reference', 0):,}
- **Human Verification Preparation**:
  - Actual measured language review queue count: {audit_results['actual_language_review_queue_count']:,} cases (written to `results/phase2_v2/language_review_queue.json`).
  - Balanced review sheet prepared at `results/phase2_v2/language_human_review_sheet.csv` with human-label columns blank.
  - Language accuracy will be reported only after actual human verification.

## Input Quality Flags Distribution (Used for Routing, Challenge Sampling & Inference)
| Input Flag | Count | Percentage |
|---|---:|---:|
| `has_url` | {input_flag_counts['has_url']:,} | {input_flag_counts['has_url']/len(all_items)*100:.1f}% |
| `private_handoff` | {input_flag_counts['private_handoff']:,} | {input_flag_counts['private_handoff']/len(all_items)*100:.1f}% |
| `external_context_required` | {input_flag_counts['external_context_required']:,} | {input_flag_counts['external_context_required']/len(all_items)*100:.1f}% |
| `suspected_multipart` | {input_flag_counts['suspected_multipart']:,} | {input_flag_counts['suspected_multipart']/len(all_items)*100:.1f}% |
| `partial_text` | {input_flag_counts['partial_text']:,} | {input_flag_counts['partial_text']/len(all_items)*100:.1f}% |

## Reference Reply Quality Flags Distribution (Historical Knowledge Metadata)
| Reply Flag | Count | Percentage |
|---|---:|---:|
| `has_url` | {reply_flag_counts['has_url']:,} | {reply_flag_counts['has_url']/len(all_items)*100:.1f}% |
| `private_handoff` | {reply_flag_counts['private_handoff']:,} | {reply_flag_counts['private_handoff']/len(all_items)*100:.1f}% |
| `external_context_required` | {reply_flag_counts['external_context_required']:,} | {reply_flag_counts['external_context_required']/len(all_items)*100:.1f}% |
| `suspected_multipart` | {reply_flag_counts['suspected_multipart']:,} | {reply_flag_counts['suspected_multipart']/len(all_items)*100:.1f}% |
| `partial_text` | {reply_flag_counts['partial_text']:,} | {reply_flag_counts['partial_text']/len(all_items)*100:.1f}% |

## Exclusions Breakdown
- Total Excluded Candidates: {exclusion_summary.get('total_excluded', 0):,}
"""
    for reason, count in sorted(exclusion_summary.get("breakdown", {}).items(), key=lambda x: -x[1]):
        content += f"- `{reason}`: {count:,}\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def generate_dev_preview_md(dev_sample: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Exports 20 development examples for human inspection.
    Includes target message, allowed prior context, source identifiers, and quality flags.
    Does NOT include automated decisions or describe them as human-verified.
    """
    content = """# Phase 2 Development Set Preview (20 Examples)

> [!NOTE]
> These 20 examples are exported for human inspection of target customer inquiries and allowed prior context.
> No automated intent labels, classification decisions, or human ratings are included.
> These examples have not yet been human-verified.

---
"""
    for idx, item in enumerate(dev_sample, 1):
        qf = item.get("quality_flags") or item.get("input_quality_flags", {})
        ancestor_turns = item["ancestor_turns"]
        prior_context = ancestor_turns[:-1] if len(ancestor_turns) > 1 else []

        content += f"## Example {idx:02d} — `{item['example_id']}`\n\n"
        content += f"- **Group ID (Root)**: `{item['group_id']}`\n"
        content += f"- **Target Customer Tweet ID**: `{item['target_customer_tweet_id']}`\n"
        content += f"- **Selected Reply Tweet ID**: `{item['selected_brand_reply_tweet_id']}`\n"
        content += f"- **Created At**: `{item['created_at']}`\n"
        content += (
            f"- **Input Quality Flags**: `url={qf.get('has_url', False)}`, "
            f"`dm={qf.get('private_handoff', False)}`, "
            f"`external_context={qf.get('external_context_required', False)}`, "
            f"`multipart={qf.get('suspected_multipart', False)}`, "
            f"`partial_text={qf.get('partial_text', False)}`\n\n"
        )

        content += "### Allowed Prior Context\n\n"
        if not prior_context:
            content += "*None (this inquiry is the conversation root turn).*\n\n"
        else:
            for turn in prior_context:
                role = "Customer" if turn.get("inbound") else f"Brand ({BRAND_NAME})"
                redacted_turn_text = redact_sensitive_info(turn.get("text", ""))
                content += f"> **[{role}]** (*Tweet ID*: `{turn['tweet_id']}`): {redacted_turn_text}\n>\n"
            content += "\n"

        content += "### Target Customer Message\n\n"
        redacted_target = redact_sensitive_info(item.get("customer_text") or item.get("raw_customer_text") or "")
        content += f"> **[Customer]**: {redacted_target}\n\n"

        content += "### Formatted Model Input\n\n"
        content += "```text\n"
        content += item["model_input_text"] + "\n"
        content += "```\n\n"

        content += "---\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    """Main execution entrypoint for Phase 2 dataset preparation."""
    print("================ PHASE 2 DATASET PREPARATION (v2) ================", flush=True)
    print(f"Target Brand           : {BRAND_NAME}")
    print(f"Historical Target      : {TARGET_HISTORICAL}")
    print(f"Dev Target             : {TARGET_DEV}")
    print(f"Eval Pool Target       : {TARGET_EVAL_POOL}")
    print(f"Random Seed            : {RANDOM_SEED}")
    print(f"Database Index         : {DB_PATH.relative_to(REPO_ROOT)}")

    # 1. Compute initial hashes of protected files
    initial_protected_hashes = hash_protected_files()
    print(f"Hashed {len(initial_protected_hashes)} protected reference files prior to execution.", flush=True)

    # 2. Validate index and source dataset checksum
    db_meta = validate_or_rebuild_index(DB_PATH, DEFAULT_DATASET_PATH, rebuild_if_invalid=True)
    source_checksum = db_meta.get("source_csv_sha256") or compute_file_sha256(DEFAULT_DATASET_PATH)
    actual_csv_checksum = compute_file_sha256(DEFAULT_DATASET_PATH)
    if source_checksum != actual_csv_checksum:
        raise ValueError(
            f"Source CSV SHA256 mismatch: db metadata={source_checksum} vs file={actual_csv_checksum}"
        )
    print(f"Source Dataset SHA256 (verified): {source_checksum}", flush=True)

    review_excluded_roots = load_review_exclusion_root_ids()
    print(f"Loaded {len(review_excluded_roots)} review root IDs to exclude from eval pool.", flush=True)

    conn = get_db_connection(DB_PATH)
    cursor = conn.cursor()
    candidates, raw_exclusions, uncertain_language, non_english_cases = extract_phase2_candidates(
        cursor, review_excluded_roots, return_non_english=True
    )
    conn.close()

    dedup_candidates, leakage_audit, exact_dups_removed = deduplicate_and_audit_leakage(candidates)

    total_exclusions = sum(raw_exclusions.values()) + exact_dups_removed
    language_state_counts = {
        "english": len(candidates),
        "non_english": len(non_english_cases),
        "uncertain": len(uncertain_language),
    }
    inclusion_decision_counts = {
        "included_english_eligible": len(candidates),
        "excluded_uncertain_pending_review": len(uncertain_language),
        "excluded_non_english": len(non_english_cases),
        "excluded_uninterpretable": sum(v for k, v in raw_exclusions.items() if k.startswith("UNINTERPRETABLE")),
        "excluded_structural_or_reference": sum(v for k, v in raw_exclusions.items() if k.startswith("STRUCTURAL") or "REFERENCE" in k or "MISSING" in k),
    }

    exclusion_summary = {
        "total_excluded": total_exclusions,
        "review_groups_blacklisted_from_eval": len(review_excluded_roots),
        "exact_duplicates_removed": exact_dups_removed,
        "language_state_counts": language_state_counts,
        "inclusion_decision_counts": inclusion_decision_counts,
        "uncertain_language_cases_count": len(uncertain_language),
        "uncertain_language_sample": uncertain_language[:20],
        "breakdown": {
            **raw_exclusions,
            "EXACT_DUPLICATE_INQUIRY": exact_dups_removed
        }
    }

    dev_set, eval_pool, historical_corpus, all_partitioned = create_partitions(
        dedup_candidates,
        target_historical=TARGET_HISTORICAL,
        target_dev=TARGET_DEV,
        target_eval_pool=TARGET_EVAL_POOL,
        seed=RANDOM_SEED
    )

    dev_groups = {x["group_id"] for x in dev_set}
    eval_groups = {x["group_id"] for x in eval_pool}
    hist_groups = {x["group_id"] for x in historical_corpus}

    dev_eval_overlap = len(dev_groups & eval_groups)
    dev_hist_overlap = len(dev_groups & hist_groups)
    eval_hist_overlap = len(eval_groups & hist_groups)
    review_eval_overlap = len(eval_groups & review_excluded_roots)

    leakage_audit["partition_leakage_audit"] = {
        "dev_eval_group_overlap": dev_eval_overlap,
        "dev_historical_group_overlap": dev_hist_overlap,
        "eval_historical_group_overlap": eval_hist_overlap,
        "review_eval_pool_overlap": review_eval_overlap,
        "leakage_detected": any([dev_eval_overlap, dev_hist_overlap, eval_hist_overlap, review_eval_overlap])
    }

    if leakage_audit["partition_leakage_audit"]["leakage_detected"]:
        raise ValueError("CRITICAL: Partition overlap or review contamination detected during leakage audit!")

    # Balanced sample for human check preparation: 10 accepted, 10 rejected, 10 uncertain
    accepted_sample = [
        {**item, "sample_category": "accepted"}
        for item in dev_set[:10]
    ]
    rejected_sample = non_english_cases[:10]
    uncertain_sample = uncertain_language[:10]
    sample_review_records = accepted_sample + rejected_sample + uncertain_sample

    # Export outputs to v2 directories
    export_phase2_outputs(
        dev_set, eval_pool, historical_corpus, all_partitioned,
        exclusion_summary, leakage_report=leakage_audit, source_checksum=source_checksum,
        uncertain_language_cases=uncertain_language,
        sample_review_records=sample_review_records,
    )

    # Run independent disk audit against exported files
    audit_results = audit_exported_dataset_on_disk(
        data_dir=OUTPUT_DATA_DIR,
        manifest_dir=OUTPUT_MANIFEST_DIR,
        report_dir=OUTPUT_REPORT_DIR,
        review_excluded_roots=review_excluded_roots,
        expected_source_csv_sha256=source_checksum,
    )
    print(f"Disk audit passed: {audit_results['total_partitioned_groups']} groups verified on disk.", flush=True)

    # Generate data summary markdown with measured disk values
    summary_md_path = OUTPUT_REPORT_DIR / "data_summary.md"
    generate_data_summary_md(
        dev_set, eval_pool, historical_corpus,
        exclusion_summary, leakage_audit, audit_results,
        summary_md_path
    )
    print(f"Wrote data summary to {_safe_relpath(summary_md_path)}", flush=True)

    # Verify protected reference files unchanged
    verify_protected_files(initial_protected_hashes)
    print(f"Verified all {len(initial_protected_hashes)} protected reference files unchanged.", flush=True)

    manifest_sha256 = compute_file_sha256(OUTPUT_MANIFEST_DIR / "split_manifest.jsonl")
    print(f"Split Manifest SHA-256: {manifest_sha256}", flush=True)

    print("================ PHASE 2 PREPARATION COMPLETE ================", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"Error during Phase 2 dataset preparation: {err}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
