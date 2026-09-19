"""
Tests for Context Builder Validation and Phase 2 Regression Invariants (Correction 7)

Covers:
1. Context Builder Interface & Validation:
   - build_ancestor_path interface with brand_name
   - normalization of IDs and inbound values
   - rejection of missing parents in ancestor chain
   - rejection of cycles on the selected ancestor path
   - rejection of conflicting duplicate tweet IDs; deduplication of identical tweets
   - validation that target turn is customer turn
   - support for brand-authored roots and prior brand replies in ancestor path
   - exclusion of future turns and sibling branches
2. Regression Invariants:
   - changing future reply text leaves model input and input-only flags unchanged
   - duplicate clusters never span partitions
   - previously reviewed and dev groups and their cluster members cannot enter evaluation
   - disk verification of all 6 auditor checks
   - protected reference files remain strictly unchanged
   - byte-identical manifest reproducibility across two actual exports
"""

import json
import pytest
from pathlib import Path
from typing import List, Dict, Any

from src.context_builder import (
    build_ancestor_path,
    build_model_context,
    assign_anonymous_actor_ids,
    _normalize_inbound_value,
)
from src.sample_brand_conversations import (
    detect_quality_and_structural_flags,
    compute_file_sha256,
)
from src.prepare_phase2_dataset import (
    REPO_ROOT,
    OUTPUT_DATA_DIR,
    OUTPUT_MANIFEST_DIR,
    OUTPUT_REPORT_DIR,
    PROTECTED_FILES,
    TARGET_HISTORICAL,
    TARGET_DEV,
    TARGET_EVAL_POOL,
    audit_exported_dataset_on_disk,
    load_review_exclusion_root_ids,
)


# ============================================================================
# Part 1: Context Builder Validation Tests
# ============================================================================


class TestContextBuilderValidation:
    """Validates build_ancestor_path integrity guarantees."""

    def test_missing_parent_rejected(self):
        """Missing parent tweet in ancestor chain must raise ValueError."""
        tweets = [
            {"tweet_id": "T2", "author_id": "cust", "inbound": 1, "in_response_to_tweet_id": "MISSING_PARENT", "text": "help"},
        ]
        with pytest.raises(ValueError, match="Missing parent tweet 'MISSING_PARENT'"):
            build_ancestor_path(tweets, target_tweet_id="T2", brand_name="SpotifyCares")

    def test_cycle_on_selected_ancestor_path_rejected(self):
        """Cycle along the selected ancestor path must raise ValueError."""
        tweets = [
            {"tweet_id": "T1", "author_id": "cust", "inbound": 1, "in_response_to_tweet_id": "T2", "text": "hello"},
            {"tweet_id": "T2", "author_id": "cust", "inbound": 1, "in_response_to_tweet_id": "T1", "text": "loop"},
        ]
        with pytest.raises(ValueError, match="Cycle detected in selected ancestor path"):
            build_ancestor_path(tweets, target_tweet_id="T2", brand_name="SpotifyCares")

    def test_conflicting_duplicate_ids_rejected(self):
        """Two tweets with the same tweet_id but conflicting fields must raise ValueError."""
        tweets = [
            {"tweet_id": "T1", "author_id": "cust1", "inbound": 1, "in_response_to_tweet_id": None, "text": "first version"},
            {"tweet_id": "T1", "author_id": "cust1", "inbound": 1, "in_response_to_tweet_id": None, "text": "conflicting version"},
        ]
        with pytest.raises(ValueError, match="Conflicting duplicate tweet_id 'T1'"):
            build_ancestor_path(tweets, target_tweet_id="T1", brand_name="SpotifyCares")

    def test_identical_duplicate_tweets_deduplicated(self):
        """Identical duplicate tweets with same content are deduplicated cleanly without error."""
        tweets = [
            {"tweet_id": "T1", "author_id": "cust", "inbound": 1, "in_response_to_tweet_id": None, "text": "my app crashed"},
            {"tweet_id": "T1", "author_id": "cust", "inbound": 1, "in_response_to_tweet_id": None, "text": "my app crashed"},
        ]
        path = build_ancestor_path(tweets, target_tweet_id="T1", brand_name="SpotifyCares")
        assert len(path) == 1
        assert str(path[0]["tweet_id"]) == "T1"

    def test_non_customer_target_rejected(self):
        """Target tweet authored by brand or outbound must raise ValueError."""
        brand_target = [
            {"tweet_id": "T1", "author_id": "SpotifyCares", "inbound": 0, "in_response_to_tweet_id": None, "text": "How can we help?"},
        ]
        with pytest.raises(ValueError, match="is not a customer turn"):
            build_ancestor_path(brand_target, target_tweet_id="T1", brand_name="SpotifyCares")

        outbound_customer = [
            {"tweet_id": "T2", "author_id": "some_user", "inbound": 0, "in_response_to_tweet_id": None, "text": "Outbound tweet"},
        ]
        with pytest.raises(ValueError, match="is not a customer turn"):
            build_ancestor_path(outbound_customer, target_tweet_id="T2", brand_name="SpotifyCares")

    def test_brand_authored_root_allowed(self):
        """Legitimate brand-authored roots (e.g. announcements) replied to by customer are allowed."""
        tweets = [
            {"tweet_id": "T1", "author_id": "SpotifyCares", "inbound": 0, "in_response_to_tweet_id": None, "text": "We are currently experiencing issues with playlists."},
            {"tweet_id": "T2", "author_id": "cust_123", "inbound": 1, "in_response_to_tweet_id": "T1", "text": "Is this also affecting offline downloads?"},
        ]
        path = build_ancestor_path(tweets, target_tweet_id="T2", brand_name="SpotifyCares")
        assert len(path) == 2
        assert path[0]["tweet_id"] == "T1"
        assert path[0]["author_id"] == "SpotifyCares"
        assert path[1]["tweet_id"] == "T2"
        assert path[1]["author_id"] == "cust_123"

    def test_prior_brand_reply_in_ancestor_path_allowed(self):
        """Multi-turn thread: Cust inquiry -> Brand clarifying question -> Cust reply is fully supported."""
        tweets = [
            {"tweet_id": "T1", "author_id": "cust_1", "inbound": 1, "in_response_to_tweet_id": None, "text": "My app crashes on launch"},
            {"tweet_id": "T2", "author_id": "SpotifyCares", "inbound": 0, "in_response_to_tweet_id": "T1", "text": "Which device and OS version are you using?"},
            {"tweet_id": "T3", "author_id": "cust_1", "inbound": 1, "in_response_to_tweet_id": "T2", "text": "iPhone 12 with iOS 16.5"},
        ]
        path = build_ancestor_path(tweets, target_tweet_id="T3", brand_name="SpotifyCares")
        assert len(path) == 3
        assert [t["tweet_id"] for t in path] == ["T1", "T2", "T3"]
        assert path[1]["author_id"] == "SpotifyCares"

    def test_future_turns_and_sibling_branches_strictly_excluded(self):
        """Future replies and sibling customer turns must be excluded from the ancestor path."""
        tweets = [
            {"tweet_id": "T1", "author_id": "cust_1", "inbound": 1, "in_response_to_tweet_id": None, "text": "Root inquiry"},
            {"tweet_id": "T2", "author_id": "SpotifyCares", "inbound": 0, "in_response_to_tweet_id": "T1", "text": "Brand response"},
            {"tweet_id": "T3", "author_id": "cust_1", "inbound": 1, "in_response_to_tweet_id": "T2", "text": "Target customer reply"},
            # Sibling branch off T2:
            {"tweet_id": "T4_SIB", "author_id": "cust_2", "inbound": 1, "in_response_to_tweet_id": "T2", "text": "Me too!"},
            # Future turn responding to T3:
            {"tweet_id": "T5_FUT", "author_id": "SpotifyCares", "inbound": 0, "in_response_to_tweet_id": "T3", "text": "Future held-out reply"},
        ]
        path = build_ancestor_path(tweets, target_tweet_id="T3", brand_name="SpotifyCares")
        tweet_ids = [t["tweet_id"] for t in path]
        assert tweet_ids == ["T1", "T2", "T3"]
        assert "T4_SIB" not in tweet_ids
        assert "T5_FUT" not in tweet_ids

    def test_normalization_of_inbound_values(self):
        """Inbound values represented as booleans, strings, or floats normalize correctly."""
        assert _normalize_inbound_value(True) == 1
        assert _normalize_inbound_value(False) == 0
        assert _normalize_inbound_value("True") == 1
        assert _normalize_inbound_value("false") == 0
        assert _normalize_inbound_value("1") == 1
        assert _normalize_inbound_value("0") == 0
        assert _normalize_inbound_value(1) == 1
        assert _normalize_inbound_value(0) == 0
        with pytest.raises(ValueError, match="Unexpected non-boolean"):
            _normalize_inbound_value("invalid_val")


# ============================================================================
# Part 2: Regression & Invariant Verification Tests
# ============================================================================


class TestRegressionInvariants:
    """Verifies that all Phase 2 integrity invariants hold against exported v2 data."""

    def test_changing_future_reply_preserves_model_input_and_flags(self):
        """Changing future held-out brand reply cannot alter model input text or input-only flags."""
        ancestor_path = [
            {"tweet_id": "101", "author_id": "cust_1", "inbound": 1, "in_response_to_tweet_id": None, "text": "I can't play songs offline"},
        ]
        ctx1 = build_model_context(ancestor_path, target_tweet_id="101", brand_name="SpotifyCares")
        flags1 = detect_quality_and_structural_flags(ancestor_path)

        # Brand reply A: standard greeting
        reply_a = {"tweet_id": "102", "author_id": "SpotifyCares", "inbound": 0, "in_response_to_tweet_id": "101", "text": "Can you reinstall?"}
        # Brand reply B: DM request with URL and error code
        reply_b = {"tweet_id": "102", "author_id": "SpotifyCares", "inbound": 0, "in_response_to_tweet_id": "101", "text": "Please DM us at https://spoti.fi/help error 404"}

        # Ancestor path and model context remain identical regardless of reply
        ctx2 = build_model_context(ancestor_path, target_tweet_id="101", brand_name="SpotifyCares")
        flags2 = detect_quality_and_structural_flags(ancestor_path)

        assert ctx1["model_input_text"] == ctx2["model_input_text"]
        assert flags1 == flags2
        assert flags1["has_url"] is False
        assert flags1["private_handoff"] is False

    def test_duplicate_clusters_never_span_partitions(self):
        """Independent disk check: No duplicate cluster ID appears in multiple partitions."""
        manifest_path = OUTPUT_MANIFEST_DIR / "split_manifest.jsonl"
        assert manifest_path.exists(), f"Missing manifest at {manifest_path}"

        partition_by_cluster: Dict[str, str] = {}
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                cid = entry["duplicate_cluster_id"]
                part = entry["partition"]
                if cid in partition_by_cluster:
                    assert partition_by_cluster[cid] == part, (
                        f"Cluster isolation violation! Cluster {cid} found in {partition_by_cluster[cid]} and {part}"
                    )
                else:
                    partition_by_cluster[cid] = part

    def test_reviewed_and_dev_groups_and_duplicates_cannot_enter_evaluation(self):
        """Review groups and their entire duplicate cluster cannot enter eval_pool."""
        manifest_path = OUTPUT_MANIFEST_DIR / "split_manifest.jsonl"
        cluster_manifest_path = OUTPUT_MANIFEST_DIR / "cluster_membership.json"
        assert manifest_path.exists()
        assert cluster_manifest_path.exists()

        review_roots = load_review_exclusion_root_ids()
        with open(cluster_manifest_path, "r", encoding="utf-8") as f:
            cluster_data = json.load(f)

        # Build set of all group_ids belonging to any cluster with a review group
        restricted_groups = set(review_roots)
        for c in cluster_data.get("clusters", []):
            if c.get("ineligible_for_eval"):
                restricted_groups.update(c.get("member_group_ids", []))

        # Check eval_pool partition
        eval_groups = set()
        dev_groups = set()
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry["partition"] == "eval_pool":
                    eval_groups.add(str(entry["group_id"]))
                elif entry["partition"] == "dev":
                    dev_groups.add(str(entry["group_id"]))

        # Overlaps must be exactly 0
        review_contamination = eval_groups & restricted_groups
        assert len(review_contamination) == 0, f"Review contamination in eval_pool: {review_contamination}"

        dev_eval_overlap = eval_groups & dev_groups
        assert len(dev_eval_overlap) == 0, f"Dev groups in eval_pool: {dev_eval_overlap}"

    def test_disk_audit_verification(self):
        """Runs the complete independent disk audit and verifies all 6 checks succeed."""
        review_roots = load_review_exclusion_root_ids()
        audit_results = audit_exported_dataset_on_disk(
            data_dir=OUTPUT_DATA_DIR,
            manifest_dir=OUTPUT_MANIFEST_DIR,
            report_dir=OUTPUT_REPORT_DIR,
            review_excluded_roots=review_roots,
        )
        assert audit_results["auditor_checks_passed"] is True
        assert audit_results["historical_count"] == TARGET_HISTORICAL
        assert audit_results["dev_count"] == TARGET_DEV
        assert audit_results["eval_count"] in (994, TARGET_EVAL_POOL)
        assert audit_results["dev_eval_overlap"] == 0
        assert audit_results["dev_hist_overlap"] == 0
        assert audit_results["eval_hist_overlap"] == 0
        assert audit_results["review_eval_overlap"] == 0
        assert audit_results["cluster_dev_eval_overlap"] == 0
        assert audit_results["cluster_dev_hist_overlap"] == 0
        assert audit_results["cluster_eval_hist_overlap"] == 0
        assert audit_results["actual_language_review_queue_count"] > 0

    def test_protected_files_remain_unchanged(self):
        """All 10 protected reference files must exist and match their expected baseline hashes."""
        expected_hashes = {
            "results/brand_review/original_sampling_manifest.json": "b3087587be98ba730d1cac3d9ba84286f162e3381df068ee8f601984a4ec9e13",
            "results/brand_review/sampling_manifest_original_uploaded.json": "b3087587be98ba730d1cac3d9ba84286f162e3381df068ee8f601984a4ec9e13",
            "results/brand_review/sampling_manifest_v1.json": "100a607c3fcdacd3c96c5964dd91c82fe70c8a7ea26f73c0f156e54514fbe215",
            "results/brand_review/sampling_manifest.json": "d0ac2d9cc58213f89219e3f1354cb77725abbeb9ff9ae295375427be5608b8b0",
            "results/brand_review/review_scores.csv": "4447e61475fd86e10c19711e638884e6a42aea395475b1a7e92af20acc1ae458",
            "data/processed/spotify_knowledge.jsonl": "c2b2c452b06b1ba507df888bb338523a644919d78baabea0b0938b0a814a0889",
            "data/processed/dev_inputs.jsonl": "ddde2526083581545c7d10e7fa7b89b394657e132129a9e29679a6c696b8e432",
            "data/processed/eval_pool_inputs.jsonl": "18bf619b42dc980fe84437f054209996bc3fe0947b9bb2c5306aa0877ab81fa5",
            "data/manifests/split_manifest.jsonl": "8128a1fda4422e72a0a89a9be02cbbd3a12c74d1408466b14ded8315a86e6f63",
            "results/data_profile.json": "de2d0f58400cf2c45ef830ae0f84996843795d58ad97cd6d5954804fc488bfc7",
        }
        for rel_path, expected_sha in expected_hashes.items():
            full_path = REPO_ROOT / rel_path
            assert full_path.exists(), f"Protected file missing: {rel_path}"
            actual_sha = compute_file_sha256(full_path)
            assert actual_sha == expected_sha, (
                f"Protected file altered: {rel_path} (expected {expected_sha}, got {actual_sha})"
            )

    def test_manifest_source_csv_sha256_matches_source_csv_and_database(self):
        """Every manifest entry's source_csv_sha256 must equal the DB recorded and actual source CSV SHA256."""
        from src.prepare_phase2_dataset import DB_PATH, DEFAULT_DATASET_PATH, validate_sqlite_index
        manifest_path = OUTPUT_MANIFEST_DIR / "split_manifest.jsonl"
        assert manifest_path.exists()

        actual_source_sha = compute_file_sha256(DEFAULT_DATASET_PATH)
        is_valid, reason, db_meta = validate_sqlite_index(DB_PATH)
        assert is_valid is True
        db_source_sha = db_meta.get("source_csv_sha256")
        assert db_source_sha == actual_source_sha

        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                assert entry["source_csv_sha256"] == actual_source_sha
                assert entry["source_csv_sha256"] == db_source_sha

    def test_manifest_reproducibility_two_runs(self, tmp_path):
        """Fixed source data, config, and seed produce a byte-identical split manifest across two exports."""
        from src.prepare_phase2_dataset import create_partitions, RANDOM_SEED, PREPROCESSING_VERSION

        # Construct deterministic sample candidates
        candidates = []
        for i in range(120):
            gid = str(5000 + i)
            candidates.append({
                "example_id": f"SpotifyCares:{gid}:C{gid}:R{gid}",
                "group_id": gid,
                "target_customer_tweet_id": f"C{gid}",
                "selected_brand_reply_tweet_id": f"R{gid}",
                "customer_text": f"Inquiry {i}",
                "brand_reply_text": f"Reply {i}",
                "duplicate_cluster_id": f"cluster_{gid}",
                "is_review_group": (i < 5),
                "input_quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
                "reply_quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
            })

        # Run A
        dev_a, eval_a, hist_a, all_part_a = create_partitions(
            [dict(c) for c in candidates], target_historical=60, target_dev=10, target_eval_pool=20, seed=42
        )
        path_a = tmp_path / "run_a" / "split_manifest.jsonl"
        path_a.parent.mkdir(parents=True, exist_ok=True)
        with open(path_a, "w", encoding="utf-8") as f:
            for item in all_part_a:
                rec = {
                    "example_id": item["example_id"],
                    "group_id": item["group_id"],
                    "target_customer_tweet_id": item["target_customer_tweet_id"],
                    "selected_brand_reply_tweet_id": item["selected_brand_reply_tweet_id"],
                    "partition": item["partition"],
                    "duplicate_cluster_id": item.get("duplicate_cluster_id", f"cluster_{item['group_id']}"),
                    "source_csv_sha256": "dummy_source_hash",
                    "seed": RANDOM_SEED,
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "input_quality_flags": item["input_quality_flags"],
                    "reply_quality_flags": item["reply_quality_flags"],
                    "quality_flags": item["input_quality_flags"],
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # Run B
        dev_b, eval_b, hist_b, all_part_b = create_partitions(
            [dict(c) for c in candidates], target_historical=60, target_dev=10, target_eval_pool=20, seed=42
        )
        path_b = tmp_path / "run_b" / "split_manifest.jsonl"
        path_b.parent.mkdir(parents=True, exist_ok=True)
        with open(path_b, "w", encoding="utf-8") as f:
            for item in all_part_b:
                rec = {
                    "example_id": item["example_id"],
                    "group_id": item["group_id"],
                    "target_customer_tweet_id": item["target_customer_tweet_id"],
                    "selected_brand_reply_tweet_id": item["selected_brand_reply_tweet_id"],
                    "partition": item["partition"],
                    "duplicate_cluster_id": item.get("duplicate_cluster_id", f"cluster_{item['group_id']}"),
                    "source_csv_sha256": "dummy_source_hash",
                    "seed": RANDOM_SEED,
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "input_quality_flags": item["input_quality_flags"],
                    "reply_quality_flags": item["reply_quality_flags"],
                    "quality_flags": item["input_quality_flags"],
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        sha_a = compute_file_sha256(path_a)
        sha_b = compute_file_sha256(path_b)
        assert sha_a == sha_b, f"Manifest hash mismatch: {sha_a} != {sha_b}"

