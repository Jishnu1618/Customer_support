"""
Tests for Phase 2 Dataset Preparation & Verification

Tests:
1. Language detection on English, multilingual, and short queries
2. Interpretability filtering
3. Exact duplicate inquiry deduplication
4. Split isolation (no group overlap across partitions)
5. Review group blacklist enforcement (excluded from eval_pool)
6. Model inputs exclusion of brand reply
7. Deterministic reproducibility
8. Manifest schema and standard example_id format
9. Existing review files preservation
"""

import json
import pytest
from pathlib import Path

from src.prepare_phase2_dataset import (
    detect_english_language,
    is_interpretable_support_content,
    is_contextually_interpretable,
    normalize_inquiry_for_dedup,
    deduplicate_and_audit_leakage,
    create_partitions,
    load_review_exclusion_root_ids,
    REPO_ROOT,
    BRAND_REVIEW_DIR,
)


class TestLanguageDetection:
    """Tests for rule-based English language detection."""

    def test_english_inquiry_accepted(self):
        text = "@SpotifyCares my app is crashing every time I open my playlist on iPhone"
        is_eng, conf, reason, is_unc = detect_english_language(text)
        assert is_eng is True
        assert conf >= 0.5
        assert reason in ["english_stopwords_match", "single_english_stopword"]

    def test_spanish_inquiry_rejected(self):
        text = "@SpotifyCares hola no puedo reproducir mi musica en mi cuenta por favor ayuda"
        is_eng, conf, reason, is_unc = detect_english_language(text)
        assert is_eng is False
        assert reason == "non_english_stopwords"

    def test_portuguese_inquiry_rejected(self):
        text = "@SpotifyCares boa tarde não consigo ouvir minhas músicas offline com o meu celular"
        is_eng, conf, reason, is_unc = detect_english_language(text)
        assert is_eng is False
        assert reason == "non_english_stopwords"

    def test_non_latin_script_rejected(self):
        text = "@SpotifyCares Помогите пожалуйста приложение не работает"
        is_eng, conf, reason, is_unc = detect_english_language(text)
        assert is_eng is False
        assert reason == "non_latin_script"

    def test_empty_or_too_short(self):
        is_eng, _, reason, _ = detect_english_language("")
        assert is_eng is False
        assert reason == "empty_text"

        is_eng, _, reason, _ = detect_english_language("hi")
        assert is_eng is False
        assert reason == "too_short"


class TestInterpretabilityFilter:
    """Tests for interpretable support content validation."""

    def test_valid_inquiry_accepted(self):
        cust = "My playlist disappeared after the latest iOS update"
        reply = "Let's check this out! Can you let us know your device model?"
        valid, reason = is_interpretable_support_content(cust, reply)
        assert valid is True
        assert reason == "valid"

    def test_bare_handle_rejected(self):
        cust = "@SpotifyCares"
        reply = "Hey, how can we help?"
        valid, reason = is_interpretable_support_content(cust, reply)
        assert valid is False
        assert "short" in reason or "empty" in reason

    def test_insufficient_content_words_rejected(self):
        cust = "@SpotifyCares help"
        reply = "Hey, what seems to be the issue?"
        valid, reason = is_interpretable_support_content(cust, reply)
        assert valid is False
        assert reason == "insufficient_content_words"

    def test_changing_future_reply_cannot_change_interpretability(self):
        cust = "I cannot log in to my premium account"
        # Reply is held out and must not influence interpretability
        valid_empty, _ = is_contextually_interpretable(cust, ancestor_turns=None)
        valid_with_reply, _ = is_interpretable_support_content(cust, reply_text="Hey! Send us a DM.")
        assert valid_empty is True
        assert valid_with_reply is True



class TestDeduplicationAndLeakage:
    """Tests for exact duplicate inquiry deduplication across conversation groups."""

    def test_exact_duplicates_across_groups_deduplicated(self):
        candidates = [
            {
                "group_id": "100",
                "target_customer_tweet_id": "C100",
                "normalized_inquiry": "my spotify app keeps crashing",
            },
            {
                "group_id": "101",
                "target_customer_tweet_id": "C101",
                "normalized_inquiry": "my spotify app keeps crashing",  # exact duplicate
            },
            {
                "group_id": "102",
                "target_customer_tweet_id": "C102",
                "normalized_inquiry": "cannot play downloaded tracks offline",  # unique
            },
        ]
        deduped, audit, removed_count = deduplicate_and_audit_leakage(candidates)
        assert len(deduped) == 2
        assert removed_count == 1
        assert audit["exact_duplicates_removed"] == 1
        # Canonical is earliest group_id (100)
        retained_groups = {x["group_id"] for x in deduped}
        assert "100" in retained_groups
        assert "102" in retained_groups
        assert "101" not in retained_groups


class TestPartitionIsolation:
    """Tests for split isolation, no group overlap, and review group blacklisting."""

    def _make_dummy_candidates(self, n=150, review_count=10):
        candidates = []
        for i in range(n):
            gid = str(1000 + i)
            candidates.append({
                "example_id": f"SpotifyCares:{gid}:C{gid}:R{gid}",
                "group_id": gid,
                "target_customer_tweet_id": f"C{gid}",
                "selected_brand_reply_tweet_id": f"R{gid}",
                "customer_text": f"Customer issue number {i}",
                "brand_reply_text": f"Brand reply number {i}",
                "model_input_text": f"[Customer_1]: Customer issue number {i}",
                "ancestor_turns": [{"tweet_id": f"C{gid}", "author_id": "cust", "inbound": 1, "text": f"Customer issue number {i}"}],
                "quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
                "created_at": "Mon Oct 16 10:00:00 +0000 2017",
                "is_review_group": (i < review_count),
            })
        return candidates

    def test_no_group_overlap_across_partitions(self):
        candidates = self._make_dummy_candidates(n=120, review_count=5)
        dev, eval_pool, hist, _ = create_partitions(
            candidates, target_historical=60, target_dev=10, target_eval_pool=30, seed=42
        )
        dev_g = {x["group_id"] for x in dev}
        eval_g = {x["group_id"] for x in eval_pool}
        hist_g = {x["group_id"] for x in hist}

        assert len(dev_g & eval_g) == 0
        assert len(dev_g & hist_g) == 0
        assert len(eval_g & hist_g) == 0

    def test_review_groups_never_in_eval_pool(self):
        candidates = self._make_dummy_candidates(n=100, review_count=20)
        dev, eval_pool, hist, _ = create_partitions(
            candidates, target_historical=40, target_dev=10, target_eval_pool=30, seed=42
        )
        # Verify no review group is in eval_pool
        for item in eval_pool:
            assert item["is_review_group"] is False

    def test_deterministic_reproducibility(self):
        candidates1 = self._make_dummy_candidates(n=80, review_count=5)
        candidates2 = self._make_dummy_candidates(n=80, review_count=5)

        dev1, eval1, hist1, _ = create_partitions(candidates1, target_historical=40, target_dev=10, target_eval_pool=20, seed=42)
        dev2, eval2, hist2, _ = create_partitions(candidates2, target_historical=40, target_dev=10, target_eval_pool=20, seed=42)

        assert [x["example_id"] for x in dev1] == [x["example_id"] for x in dev2]
        assert [x["example_id"] for x in eval1] == [x["example_id"] for x in eval2]
        assert [x["example_id"] for x in hist1] == [x["example_id"] for x in hist2]


class TestProvenancePreservation:
    """Verifies existing manifests and review files are preserved."""

    def test_review_scores_and_manifests_exist(self):
        assert (BRAND_REVIEW_DIR / "review_scores.csv").exists()
        assert (BRAND_REVIEW_DIR / "sampling_manifest_v1.json").exists()
        assert (BRAND_REVIEW_DIR / "sampling_manifest.json").exists()
        assert (BRAND_REVIEW_DIR / "original_sampling_manifest.json").exists()
        assert (BRAND_REVIEW_DIR / "sampling_manifest_original_uploaded.json").exists()

    def test_exclusion_root_ids_loaded(self):
        roots = load_review_exclusion_root_ids()
        assert len(roots) >= 30
        assert "2259585" in roots  # Spotify CONV_001 root


class TestInputQualityFlagsNoLeakage:
    """Regression tests: input flags must be computed strictly from ancestors without reply leakage."""

    def test_input_flags_exclude_future_reply_information(self):
        """Customer inquiry has no DM or URL; brand reply has both. Input flags must remain False."""
        from src.sample_brand_conversations import detect_quality_and_structural_flags

        ancestor_path = [
            {
                "tweet_id": "1879689",
                "author_id": "561027",
                "inbound": 1,
                "text": "Someone was able to create & confirm an acct using my email. Can you pls help me figure out if my email was compromised?"
            }
        ]
        brand_reply = {
            "tweet_id": "1879688",
            "author_id": "SpotifyCares",
            "inbound": 0,
            "text": "Hey! Please DM us your email address at https://t.co/abc and we will investigate."
        }

        # Input flags strictly from ancestors
        input_flags = detect_quality_and_structural_flags(ancestor_path)
        assert input_flags["private_handoff"] is False
        assert input_flags["has_url"] is False
        assert input_flags["external_context_required"] is False

        # Reply flags from brand reply
        reply_flags = detect_quality_and_structural_flags([brand_reply])
        assert reply_flags["private_handoff"] is True
        assert reply_flags["has_url"] is True

        # Flawed old behavior would have leaked:
        flawed_leaked_flags = detect_quality_and_structural_flags(ancestor_path + [brand_reply])
        assert flawed_leaked_flags["private_handoff"] is True
        assert flawed_leaked_flags["has_url"] is True

