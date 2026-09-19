"""
Tests for Correction 5: Apply Privacy Redaction Consistently

Verifies:
1. Shared redaction function removes synthetic handles, emails, phone numbers,
   explicitly identified bare usernames, and dataset privacy placeholders.
2. Troubleshooting details (device names, software versions, error codes, brand handles)
   are preserved.
3. Idempotency: running redaction twice does not corrupt or double-wrap existing placeholders.
4. Redaction happens BEFORE constructing shortened snippets.
5. Diagnostic reports (exclusion summaries, duplicate reports, human review sheet,
   dev previews) follow the exact same redaction rules as model inputs.
6. Model-facing payloads isolate raw identity mappings (actor_map) and raw customer IDs.
"""

import json
import re
import pytest
from pathlib import Path
from typing import Dict, Any, List

from src.sample_brand_conversations import redact_sensitive_info
from src.language_filter import export_human_review_sheet
from src.prepare_phase2_dataset import (
    generate_dev_preview_md,
    export_phase2_outputs,
    deduplicate_and_audit_leakage,
    OUTPUT_DATA_DIR,
    OUTPUT_REPORT_DIR,
    OUTPUT_MANIFEST_DIR,
)


class TestRedactionFunction:
    """Unit tests for redact_sensitive_info."""

    def test_synthetic_handles_redacted_brand_handles_preserved(self):
        text = "@listener_jane99 asked @SpotifyCares and @AppleSupport for help with @random_user_123"
        redacted = redact_sensitive_info(text)
        assert "@listener_jane99" not in redacted
        assert "@random_user_123" not in redacted
        assert "@[CUSTOMER_HANDLE]" in redacted
        assert "@SpotifyCares" in redacted
        assert "@AppleSupport" in redacted

    def test_emails_redacted(self):
        text = "Contact me at alice.smith+support@example.co.uk or bob_123@gmail.com please"
        redacted = redact_sensitive_info(text)
        assert "alice.smith+support@example.co.uk" not in redacted
        assert "bob_123@gmail.com" not in redacted
        assert redacted.count("[EMAIL_REDACTED]") == 2

    def test_phone_numbers_redacted(self):
        test_cases = [
            ("Call me at 555-867-5309 immediately", "Call me at [PHONE_REDACTED] immediately"),
            ("My cell is (800) 555-0199 thanks", "My cell is [PHONE_REDACTED] thanks"),
            ("Phone: +1 555-234-5678.", "Phone: [PHONE_REDACTED]."),
        ]
        for original, expected in test_cases:
            res = redact_sensitive_info(original)
            assert res == expected, f"Failed: '{res}' != '{expected}'"

    def test_contextual_bare_usernames_redacted(self):
        test_cases = [
            ("My username is listener_demo96", "My username is [CUSTOMER_USERNAME]"),
            ("username: listener_demo96.", "username: [CUSTOMER_USERNAME]."),
            ("Spotify username is 'listener_demo96'", "Spotify username is '[CUSTOMER_USERNAME]'"),
            ("My user name is @listener_demo96, help!", "My user name is [CUSTOMER_USERNAME], help!"),
            ("My screen name is music_fan_2024", "My screen name is [CUSTOMER_USERNAME]"),
            ("account name is listener_demo96", "account name is [CUSTOMER_USERNAME]"),
            ("login id: listener_demo96", "login id: [CUSTOMER_USERNAME]"),
            ("handle is listener_demo96", "handle is [CUSTOMER_USERNAME]"),
        ]
        for original, expected in test_cases:
            res = redact_sensitive_info(original)
            assert res == expected, f"Failed: '{res}' != '{expected}'"

    def test_dataset_privacy_placeholders_handled(self):
        text = "Placeholder __email__ and __phone__ and id::998811__credit_card__: token"
        redacted = redact_sensitive_info(text)
        assert "__email__" not in redacted
        assert "__phone__" not in redacted
        assert "__credit_card__" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "[CREDIT_CARD_REDACTED]: token" in redacted

    def test_troubleshooting_details_preserved(self):
        text = (
            "I'm on iPhone 12 running iOS 15.1.1 with Spotify v8.4.22.857. "
            "Encountered error 0xc0000005 and code 404 on my Windows 11 PC and Galaxy S21."
        )
        redacted = redact_sensitive_info(text)
        assert "iPhone 12" in redacted
        assert "iOS 15.1.1" in redacted
        assert "Spotify v8.4.22.857" in redacted
        assert "0xc0000005" in redacted
        assert "code 404" in redacted
        assert "Windows 11" in redacted
        assert "Galaxy S21" in redacted
        assert "[PHONE_REDACTED]" not in redacted

    def test_status_words_after_username_preserved(self):
        """Phrases like 'My username is locked' must not be converted to '[CUSTOMER_USERNAME]'."""
        assert redact_sensitive_info("My username is locked") == "My username is locked"
        assert redact_sensitive_info("My username is broken") == "My username is broken"
        assert redact_sensitive_info("My account name is unknown") == "My account name is unknown"
        assert redact_sensitive_info("My username is correct") == "My username is correct"

    def test_brand_greetings_preserved_customer_greetings_redacted(self):
        assert redact_sensitive_info("Hey Spotify, my sound is gone") == "Hey Spotify, my sound is gone"
        assert redact_sensitive_info("Hi SpotifyCares, help please") == "Hi SpotifyCares, help please"
        assert redact_sensitive_info("Hey Jordan, my sound is gone") == "Hey [CUSTOMER_NAME], my sound is gone"

    def test_redaction_idempotency(self):
        """Running redaction twice must produce the exact same text without corruption."""
        samples = [
            "My username is listener_demo96 and email is alice@test.com",
            "Hey Vanessa, call 555-867-5309 for account id::123__credit_card__:",
            "Already redacted @[CUSTOMER_HANDLE] and [CUSTOMER_USERNAME] and [EMAIL_REDACTED]",
            "iPhone 12 iOS 15.1.1 Spotify v8.4.22.857 code 404 error 0xc0000005",
        ]
        for s in samples:
            first_pass = redact_sensitive_info(s)
            second_pass = redact_sensitive_info(first_pass)
            assert second_pass == first_pass, f"Idempotency failed:\nFirst:  {first_pass}\nSecond: {second_pass}"
            assert "[[" not in second_pass
            assert "]]" not in second_pass


class TestReportAndSnippetRedaction:
    """Verifies that diagnostic reports and snippets follow model input redaction rules."""

    def test_redact_before_shortened_snippet(self):
        """
        Redacting after slicing would expose partially truncated sensitive tokens.
        Redacting before slicing guarantees the entire placeholder is present.
        """
        # Place sensitive username near the 50-character mark
        raw_text = "Hello support team, my official Spotify username is listener_demo96_secure_id!"
        
        # Flawed approach: slicing before redaction cuts across sensitive tokens
        flawed_snippet = raw_text[:75]
        assert "listener_demo96" in flawed_snippet

        # Correct approach: redact then slice
        redacted_full = redact_sensitive_info(raw_text)
        correct_snippet = redacted_full[:75]
        assert "listener_demo96" not in correct_snippet
        assert "[CUSTOMER_USERNAME]" in correct_snippet

    def test_human_review_sheet_contains_no_sensitive_info(self, tmp_path):
        """Verifies that export_human_review_sheet redacts both target text and prior context snippets."""
        sheet_path = tmp_path / "test_human_review_sheet.csv"
        records = [
            {
                "sample_category": "uncertain",
                "group_id": "9991",
                "target_customer_tweet_id": "T9991",
                "raw_customer_text": "My username is listener_demo96 and my email is secret@privacy.org",
                "ancestor_turns": [
                    {
                        "tweet_id": "T9990",
                        "author_id": "778899",
                        "inbound": 1,
                        "text": "Hi @SpotifyCares, call 555-867-5309 please",
                    },
                    {
                        "tweet_id": "T9991",
                        "author_id": "778899",
                        "inbound": 1,
                        "text": "My username is listener_demo96 and my email is secret@privacy.org",
                    },
                ],
                "language_state": "uncertain",
                "language_heuristic_score": 0.5,
                "detection_reason": "test_reason",
            }
        ]

        export_human_review_sheet(records, sheet_path)
        content = sheet_path.read_text(encoding="utf-8")

        # Sensitive info must be redacted
        assert "listener_demo96" not in content
        assert "secret@privacy.org" not in content
        assert "555-867-5309" not in content
        assert "778899" not in content  # Raw customer author_id anonymized

        # Placeholders must be present
        assert "[CUSTOMER_USERNAME]" in content
        assert "[EMAIL_REDACTED]" in content
        assert "[PHONE_REDACTED]" in content
        assert "[Customer]" in content

    def test_dev_preview_md_redacts_turns_and_targets(self, tmp_path):
        """Verifies generate_dev_preview_md redacts all turns and customer target messages."""
        preview_path = tmp_path / "test_preview.md"
        dev_sample = [
            {
                "example_id": "SpotifyCares:9001:T9002:T9003",
                "group_id": "9001",
                "target_customer_tweet_id": "T9002",
                "selected_brand_reply_tweet_id": "T9003",
                "customer_text": "My account name is listener_demo96 and email is user@sample.com",
                "created_at": "Mon Oct 16 10:00:00 +0000 2017",
                "quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
                "model_input_text": "[Customer_1] (TARGET CUSTOMER INQUIRY): My account name is [CUSTOMER_USERNAME] and email is [EMAIL_REDACTED]",
                "ancestor_turns": [
                    {
                        "tweet_id": "T9001",
                        "author_id": "SpotifyCares",
                        "inbound": 0,
                        "text": "Hey @listener_jane, can you tell us your device?",
                    },
                    {
                        "tweet_id": "T9002",
                        "author_id": "888999",
                        "inbound": 1,
                        "text": "My account name is listener_demo96 and email is user@sample.com",
                    },
                ],
            }
        ]

        generate_dev_preview_md(dev_sample, preview_path)
        content = preview_path.read_text(encoding="utf-8")

        assert "listener_demo96" not in content
        assert "user@sample.com" not in content
        assert "listener_jane" not in content
        assert "[CUSTOMER_USERNAME]" in content
        assert "[EMAIL_REDACTED]" in content
        assert "@[CUSTOMER_HANDLE]" in content

    def test_duplicate_audit_snippets_redacted(self):
        """Verifies duplicate report cluster_info has redacted inquiry snippets."""
        candidates = [
            {
                "group_id": "111",
                "target_customer_tweet_id": "C111",
                "customer_text": "My username is listener_demo96 and app crashes",
                "raw_customer_text": "My username is listener_demo96 and app crashes",
                "normalized_inquiry": "my username is app crashes",
            },
            {
                "group_id": "112",
                "target_customer_tweet_id": "C112",
                "customer_text": "My username is listener_demo96 and app crashes",
                "raw_customer_text": "My username is listener_demo96 and app crashes",
                "normalized_inquiry": "my username is app crashes",
            },
        ]

        _, audit, removed_count = deduplicate_and_audit_leakage(candidates)
        assert removed_count == 1
        sample_cluster = audit["exact_duplicate_clusters_sample"][0]
        assert "listener_demo96" not in sample_cluster["inquiry_snippet"]
        assert "[CUSTOMER_USERNAME]" in sample_cluster["inquiry_snippet"]


class TestModelFacingPayloadIsolation:
    """Verifies that model-facing payloads do not leak actor_map or raw customer author IDs."""

    def test_model_facing_payloads_exclude_actor_map_and_raw_ids(self, tmp_path, monkeypatch):
        """dev_inputs.jsonl and eval_pool_inputs.jsonl must not contain actor_map or raw customer IDs."""
        test_out_dir = tmp_path / "data"
        test_rep_dir = tmp_path / "reports"
        test_man_dir = tmp_path / "manifests"

        monkeypatch.setattr("src.prepare_phase2_dataset.OUTPUT_DATA_DIR", test_out_dir)
        monkeypatch.setattr("src.prepare_phase2_dataset.OUTPUT_REPORT_DIR", test_rep_dir)
        monkeypatch.setattr("src.prepare_phase2_dataset.OUTPUT_MANIFEST_DIR", test_man_dir)

        dev_item = {
            "example_id": "SpotifyCares:5001:C5001:R5001",
            "group_id": "5001",
            "target_customer_tweet_id": "C5001",
            "selected_brand_reply_tweet_id": "R5001",
            "customer_text": "My username is [CUSTOMER_USERNAME]",
            "brand_reply_text": "Thanks for reaching out!",
            "model_input_text": "[Customer_1] (TARGET CUSTOMER INQUIRY): My username is [CUSTOMER_USERNAME]",
            "actor_map": {"998877": "Customer_1", "SpotifyCares": "SpotifyCares"},
            "ancestor_turns": [
                {
                    "tweet_id": "C5001",
                    "author_id": "998877",  # Raw customer author ID
                    "inbound": 1,
                    "created_at": "Mon Oct 16 10:00:00 +0000 2017",
                    "text": "My username is listener_demo96",
                }
            ],
            "input_quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
            "reply_quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
            "created_at": "Mon Oct 16 10:00:00 +0000 2017",
            "is_review_group": False,
        }

        export_phase2_outputs(
            dev_set=[dev_item],
            eval_pool=[dev_item],
            historical_corpus=[dev_item],
            all_partitioned=[{**dev_item, "partition": "dev"}],
            exclusion_summary={},
            leakage_report={},
            source_checksum="abc123sha",
        )

        dev_path = test_out_dir / "dev_inputs.jsonl"
        eval_path = test_out_dir / "eval_pool_inputs.jsonl"

        for path in [dev_path, eval_path]:
            with open(path, "r", encoding="utf-8") as f:
                record = json.loads(f.readline())

            # 1. actor_map must NOT be in model-facing payload
            assert "actor_map" not in record

            # 2. Raw customer ID (998877) must NOT be in ancestor turns
            for turn in record["ancestor_turns"]:
                assert turn["author_id"] != "998877"
                assert turn["author_id"] in ["Customer_1", "SpotifyCares"]
                assert "listener_demo96" not in turn["text"]
                assert "[CUSTOMER_USERNAME]" in turn["text"]
