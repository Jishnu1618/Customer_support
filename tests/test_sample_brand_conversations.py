"""
Tests for src/sample_brand_conversations.py
"""

import random
import pytest
from src.sample_brand_conversations import (
    redact_sensitive_info,
    detect_quality_and_structural_flags,
    find_root_tweet,
    collect_thread_tree,
)


def test_redact_sensitive_info_customer_handle():
    """Verify customer handles are redacted while brand handles are preserved."""
    input_text = "Hey @SpotifyCares I need help with my account, ask @john_doe"
    redacted = redact_sensitive_info(input_text, candidate_brands=["SpotifyCares"])
    
    assert "@SpotifyCares" in redacted
    assert "@[CUSTOMER_HANDLE]" in redacted
    assert "@john_doe" not in redacted


def test_redact_sensitive_info_email():
    """Verify email addresses are redacted."""
    input_text = "Contact me at alice.smith@example.com for details"
    redacted = redact_sensitive_info(input_text)
    
    assert "[EMAIL_REDACTED]" in redacted
    assert "alice.smith@example.com" not in redacted


def test_redact_sensitive_info_phone():
    """Verify phone numbers are redacted."""
    input_text = "Call me at 555-867-5309 or +1-800-555-0199"
    redacted = redact_sensitive_info(input_text)
    
    assert "[PHONE_REDACTED]" in redacted
    assert "555-867-5309" not in redacted


def test_redact_bare_username_synthetic():
    """
    Synthetic regression test for bare customer name redaction.
    Verifies that bare greeting names like 'Hey Vanessa,' are converted to 'Hey [CUSTOMER_NAME],'
    while brand mentions remain intact.
    """
    synthetic_text = "@SpotifyCares Hey Vanessa, help's here! DM us your account username"
    redacted = redact_sensitive_info(synthetic_text, candidate_brands=["SpotifyCares"])
    
    assert "@SpotifyCares" in redacted
    assert "Hey [CUSTOMER_NAME]," in redacted
    assert "Vanessa" not in redacted


def test_detect_quality_and_structural_flags():
    """Verify detection of quality flags (multipart, partial text, URL, DM, screenshot)."""
    tweets = [
        {"text": "so please reach back to me as soon as possible", "inbound": 1, "in_response_to_tweet_id": None},
        {"text": "Check https://t.co/xyz for details and DM us", "inbound": 0, "in_response_to_tweet_id": "1"},
        {"text": "This text is truncated...", "inbound": 1, "in_response_to_tweet_id": "2"}
    ]
    flags = detect_quality_and_structural_flags(tweets)
    
    assert flags["suspected_multipart"] is True
    assert flags["has_url"] is True
    assert flags["private_handoff"] is True
    assert flags["partial_text"] is True


def test_deterministic_group_sampling():
    """Verify random sampling is deterministic with seed 42."""
    items = [f"GROUP_{i}" for i in range(100)]
    
    rng1 = random.Random(42)
    sample1 = list(items)
    rng1.shuffle(sample1)

    rng2 = random.Random(42)
    sample2 = list(items)
    rng2.shuffle(sample2)

    assert sample1 == sample2
