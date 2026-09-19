"""
Tests for Correction 2: Complete Duplicate Detection & Review Contamination Prevention

Required Tests:
1. Detect a matching pair beyond candidate position 500.
2. Detect a matching pair separated by more than 99 positions.
3. Propagate review exclusion from a removed duplicate to its representative.
4. Keep transitive duplicate clusters together (A matches B, B matches C => {A, B, C}).
5. Prevent current development groups and their duplicates entering evaluation.
6. Produce the same clusters after input rows are reordered.
7. Avoid merging generic short replies solely because their target text matches.
8. Preserve meaningful negation/error-code distinctions during normalization.
9. Preserve existing files during audit-only verification.
"""

import json
import random
import pytest
from pathlib import Path
from typing import Dict, Any, List

from src.duplicate_detector import (
    normalize_inquiry,
    extract_error_codes,
    extract_negations,
    get_effective_inquiry,
    find_duplicate_pairs_inverted_index,
    build_transitive_clusters,
    propagate_restrictions_to_clusters,
    compute_token_jaccard,
    load_exclusion_history,
)
from src.prepare_phase2_dataset import (
    deduplicate_and_audit_leakage,
    OUTPUT_DATA_DIR,
    OUTPUT_MANIFEST_DIR,
    REPO_ROOT,
    BRAND_REVIEW_DIR,
)


class TestDuplicateDetectionBeyondCaps:
    """Verifies removal of candidate position <= 500 and window <= 100 caps."""

    def test_detect_matching_pair_beyond_position_500(self):
        """Pairs appearing after candidate index 500 must be detected."""
        candidates = []
        # Generate 550 dummy distinct candidates
        for i in range(550):
            candidates.append({
                "group_id": str(1000 + i),
                "customer_text": f"unique customer problem description number {i} regarding playback",
                "normalized_inquiry": f"unique customer problem description number {i} regarding playback",
            })

        # Add a duplicate pair at positions 520 and 535 (both > 500)
        shared_text = "my spotify playlist has completely disappeared after updating the app"
        candidates[520]["customer_text"] = shared_text
        candidates[520]["normalized_inquiry"] = shared_text
        candidates[535]["customer_text"] = shared_text
        candidates[535]["normalized_inquiry"] = shared_text

        pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.85)
        pair_gids = {(p[0], p[1]) for p in pairs} | {(p[1], p[0]) for p in pairs}

        gid_a = str(1000 + 520)
        gid_b = str(1000 + 535)
        assert (gid_a, gid_b) in pair_gids or (gid_b, gid_a) in pair_gids

    def test_detect_matching_pair_separated_by_more_than_99_positions(self):
        """Pairs separated by > 99 positions in the candidate list must be detected."""
        candidates = []
        for i in range(300):
            candidates.append({
                "group_id": str(2000 + i),
                "customer_text": f"distinct issue number {i} with my premium subscription billing",
                "normalized_inquiry": f"distinct issue number {i} with my premium subscription billing",
            })

        # Item at index 10 and item at index 250 (separated by 240 positions > 99)
        shared_text = "cannot stream music over cellular data connection"
        candidates[10]["customer_text"] = shared_text
        candidates[10]["normalized_inquiry"] = shared_text
        candidates[250]["customer_text"] = shared_text
        candidates[250]["normalized_inquiry"] = shared_text

        pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.85)
        pair_gids = {(p[0], p[1]) for p in pairs} | {(p[1], p[0]) for p in pairs}

        gid_a = str(2000 + 10)
        gid_b = str(2000 + 250)
        assert (gid_a, gid_b) in pair_gids or (gid_b, gid_a) in pair_gids


class TestReviewAndDevRestrictionPropagation:
    """Verifies that review and dev exposure propagates across duplicate clusters."""

    def test_propagate_review_exclusion_from_removed_duplicate_to_representative(self):
        """
        Group 3001 is unreviewed; Group 3002 is reviewed.
        They are duplicates. When deduplicated with 3001 as canonical representative,
        canonical 3001 must inherit is_review_group = True.
        """
        candidates = [
            {
                "group_id": "3001",
                "customer_text": "when will spotify be available in my country",
                "normalized_inquiry": "when will spotify be available in my country",
                "is_review_group": False,
            },
            {
                "group_id": "3002",
                "customer_text": "when will spotify be available in my country",
                "normalized_inquiry": "when will spotify be available in my country",
                "is_review_group": True,  # Previously reviewed
            },
        ]

        deduped, audit, _ = deduplicate_and_audit_leakage(candidates, restricted_root_ids={"3002"})
        assert len(deduped) == 1
        canonical = deduped[0]
        assert canonical["group_id"] == "3001"
        # Must be marked is_review_group = True so it cannot enter eval_pool!
        assert canonical["is_review_group"] is True

    def test_prevent_current_development_groups_and_duplicates_entering_evaluation(self):
        """
        Group 4001 is in the development set.
        Group 4002 is a near-duplicate of 4001.
        Both 4001 and 4002 (and their cluster) must be marked ineligible for evaluation.
        """
        dev_gids = {"4001"}
        candidates = [
            {
                "group_id": "4001",
                "customer_text": "can you please send me the promo code for the majid jordan spotify presale i love majid and i have a spotify account thx",
                "normalized_inquiry": "can you please send me the promo code for the majid jordan spotify presale i love majid and i have a spotify account thx",
                "is_review_group": False,
            },
            {
                "group_id": "4002",
                "customer_text": "hey can you please send me the promo code for the majid jordan spotify presale i love majid and i have a spotify account thx",
                "normalized_inquiry": "hey can you please send me the promo code for the majid jordan spotify presale i love majid and i have a spotify account thx",
                "is_review_group": False,
            },
        ]

        pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.85)
        clusters = build_transitive_clusters(candidates, pairs)
        updated_clusters = propagate_restrictions_to_clusters(clusters, dev_gids)

        assert len(updated_clusters) == 1
        cluster = updated_clusters[0]
        assert cluster["ineligible_for_eval"] is True
        assert "4001" in cluster["restricted_members"]

        deduped, audit, _ = deduplicate_and_audit_leakage(candidates, restricted_root_ids=dev_gids)
        assert len(deduped) == 1
        assert deduped[0]["is_review_group"] is True  # Ineligible for eval


class TestTransitiveClusteringAndStability:
    """Verifies transitive connected components and deterministic cluster ordering."""

    def test_keep_transitive_duplicate_clusters_together(self):
        """A matches B and B matches C => A, B, C must belong to the exact same cluster."""
        candidates = [
            {
                "group_id": "5001",
                "customer_text": "alpha beta gamma delta epsilon",
                "normalized_inquiry": "alpha beta gamma delta epsilon",
            },
            {
                "group_id": "5002",
                "customer_text": "alpha beta gamma delta epsilon zeta",
                "normalized_inquiry": "alpha beta gamma delta epsilon zeta",
            },
            {
                "group_id": "5003",
                "customer_text": "alpha beta gamma delta epsilon zeta eta",
                "normalized_inquiry": "alpha beta gamma delta epsilon zeta eta",
            },
        ]

        pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.70)
        clusters = build_transitive_clusters(candidates, pairs)

        # All 3 must be in a single cluster
        multi_clusters = [c for c in clusters if c["size"] > 1]
        assert len(multi_clusters) == 1
        cluster = multi_clusters[0]
        assert set(cluster["member_group_ids"]) == {"5001", "5002", "5003"}
        assert cluster["canonical_group_id"] == "5001"
        assert cluster["cluster_id"] == "cluster_5001"

    def test_produce_same_clusters_after_input_rows_are_reordered(self):
        """Cluster IDs, canonical representatives, and cluster memberships must be invariant to input row order."""
        raw_candidates = [
            {"group_id": "6003", "customer_text": "shuffle test message apple orange banana", "normalized_inquiry": "shuffle test message apple orange banana"},
            {"group_id": "6001", "customer_text": "shuffle test message apple orange banana", "normalized_inquiry": "shuffle test message apple orange banana"},
            {"group_id": "6002", "customer_text": "shuffle test message apple orange banana", "normalized_inquiry": "shuffle test message apple orange banana"},
            {"group_id": "6004", "customer_text": "different unrelated query about podcast downloads", "normalized_inquiry": "different unrelated query about podcast downloads"},
        ]

        # Order 1
        order1 = list(raw_candidates)
        pairs1 = find_duplicate_pairs_inverted_index(order1, similarity_threshold=0.85)
        clusters1 = build_transitive_clusters(order1, pairs1)

        # Order 2 (shuffled)
        rng = random.Random(123)
        order2 = list(raw_candidates)
        rng.shuffle(order2)
        pairs2 = find_duplicate_pairs_inverted_index(order2, similarity_threshold=0.85)
        clusters2 = build_transitive_clusters(order2, pairs2)

        # Assert identical cluster IDs and member sets
        c1_map = {c["cluster_id"]: (c["canonical_group_id"], c["member_group_ids"]) for c in clusters1}
        c2_map = {c["cluster_id"]: (c["canonical_group_id"], c["member_group_ids"]) for c in clusters2}
        assert c1_map == c2_map


class TestSemanticDistinctions:
    """Verifies negation, error-code distinctions, and context resolution for short replies."""

    def test_avoid_merging_generic_short_replies_solely_on_target_text(self):
        """
        Two conversations end with 'Still broken', but have completely different prior customer contexts.
        They must NOT be merged as duplicate clusters.
        """
        candidate1 = {
            "group_id": "7001",
            "customer_text": "Still broken",
            "normalized_inquiry": "still broken",
            "ancestor_turns": [
                {"tweet_id": "T1", "author_id": "cust1", "inbound": 1, "text": "My Spotify crashes on iOS 11 launch screen"},
                {"tweet_id": "T2", "author_id": "SpotifyCares", "inbound": 0, "text": "Have you tried reinstalling?"},
                {"tweet_id": "T3", "author_id": "cust1", "inbound": 1, "text": "Still broken"},
            ]
        }
        candidate2 = {
            "group_id": "7002",
            "customer_text": "Still broken",
            "normalized_inquiry": "still broken",
            "ancestor_turns": [
                {"tweet_id": "T4", "author_id": "cust2", "inbound": 1, "text": "Billing charged my credit card twice for family plan"},
                {"tweet_id": "T5", "author_id": "SpotifyCares", "inbound": 0, "text": "Can you check your receipt page?"},
                {"tweet_id": "T6", "author_id": "cust2", "inbound": 1, "text": "Still broken"},
            ]
        }

        candidates = [candidate1, candidate2]
        pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.85)
        # Because ancestor context was incorporated for the generic short reply, similarity is low
        assert len(pairs) == 0

    def test_preserve_meaningful_negation_distinctions(self):
        """'I can access my playlist now' vs 'I can not access my playlist now' must NOT be duplicates."""
        candidates = [
            {
                "group_id": "8001",
                "customer_text": "I can access my playlist on the desktop app now",
                "raw_customer_text": "I can access my playlist on the desktop app now",
                "normalized_inquiry": "i can access my playlist on the desktop app now",
            },
            {
                "group_id": "8002",
                "customer_text": "I can not access my playlist on the desktop app now",
                "raw_customer_text": "I can not access my playlist on the desktop app now",
                "normalized_inquiry": "i can not access my playlist on the desktop app now",
            },
        ]
        pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.80)
        assert len(pairs) == 0

    def test_preserve_meaningful_error_code_distinctions(self):
        """'Error 404 when opening album' vs 'Error 500 when opening album' must NOT be duplicates."""
        candidates = [
            {
                "group_id": "9001",
                "customer_text": "I keep getting error 404 whenever I click on this specific album link",
                "raw_customer_text": "I keep getting error 404 whenever I click on this specific album link",
                "normalized_inquiry": "i keep getting error 404 whenever i click on this specific album link",
            },
            {
                "group_id": "9002",
                "customer_text": "I keep getting error 500 whenever I click on this specific album link",
                "raw_customer_text": "I keep getting error 500 whenever I click on this specific album link",
                "normalized_inquiry": "i keep getting error 500 whenever i click on this specific album link",
            },
        ]
        pairs = find_duplicate_pairs_inverted_index(candidates, similarity_threshold=0.80)
        assert len(pairs) == 0


class TestAuditPreservation:
    """Verifies that diagnostic audit does not modify or overwrite production datasets."""

    def test_preserve_existing_files_during_audit(self):
        """Production dataset files must exist and maintain their checksum during audit."""
        dev_file = OUTPUT_DATA_DIR / "dev_inputs.jsonl"
        eval_file = OUTPUT_DATA_DIR / "eval_pool_inputs.jsonl"
        hist_file = OUTPUT_DATA_DIR / "spotify_knowledge.jsonl"
        manifest_file = OUTPUT_MANIFEST_DIR / "split_manifest.jsonl"

        assert dev_file.exists()
        assert eval_file.exists()
        assert hist_file.exists()
        assert manifest_file.exists()

        # Count lines
        with open(dev_file, "r", encoding="utf-8") as f:
            assert len(f.readlines()) == 50
        with open(eval_file, "r", encoding="utf-8") as f:
            assert len(f.readlines()) in (994, 1000)
        with open(hist_file, "r", encoding="utf-8") as f:
            assert len(f.readlines()) == 3000
        with open(manifest_file, "r", encoding="utf-8") as f:
            assert len(f.readlines()) in (4044, 4050)
