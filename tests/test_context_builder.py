"""
Unit Tests for src/context_builder.py

Tests ancestor path selection, sibling exclusion, future turn exclusion,
and stable anonymous actor ID assignment.
"""

import pytest
from src.context_builder import (
    build_ancestor_path,
    build_model_context,
    assign_anonymous_actor_ids,
)


def get_sample_tree_tweets():
    """
    Constructs a sample conversation tree with branching:
    - T1 (Customer A): Root inquiry
      - T2 (Brand): Brand reply to T1
        - T3 (Customer A): Customer follow-up to T2 (TARGET TURN)
          - T4 (Brand): Brand reply to T3 (FUTURE TURN - should be excluded)
        - T5 (Customer B): Unrelated sibling reply to T2 (SIBLING TURN - should be excluded)
    """
    return [
        {
            "tweet_id": "T1",
            "author_id": "Cust_A",
            "inbound": 1,
            "created_at": "Sun Oct 15 20:00:00 +0000 2017",
            "text": "My app is crashing",
            "in_response_to_tweet_id": None
        },
        {
            "tweet_id": "T2",
            "author_id": "SpotifyCares",
            "inbound": 0,
            "created_at": "Sun Oct 15 20:05:00 +0000 2017",
            "text": "What device are you using?",
            "in_response_to_tweet_id": "T1"
        },
        {
            "tweet_id": "T3",
            "author_id": "Cust_A",
            "inbound": 1,
            "created_at": "Sun Oct 15 20:10:00 +0000 2017",
            "text": "I am on iPhone 8, iOS 11",
            "in_response_to_tweet_id": "T2"
        },
        {
            "tweet_id": "T4",
            "author_id": "SpotifyCares",
            "inbound": 0,
            "created_at": "Sun Oct 15 20:15:00 +0000 2017",
            "text": "Try restarting your phone",
            "in_response_to_tweet_id": "T3"
        },
        {
            "tweet_id": "T5",
            "author_id": "Cust_B",
            "inbound": 1,
            "created_at": "Sun Oct 15 20:12:00 +0000 2017",
            "text": "Same issue here on Android",
            "in_response_to_tweet_id": "T2"
        }
    ]


def test_build_ancestor_path_excludes_future_and_siblings():
    """Verify that build_ancestor_path includes ONLY ancestors up to target turn T3."""
    tweets = get_sample_tree_tweets()
    ancestors = build_ancestor_path(tweets, target_tweet_id="T3")
    
    ancestor_ids = [t["tweet_id"] for t in ancestors]
    
    # Must contain exactly T1 -> T2 -> T3
    assert ancestor_ids == ["T1", "T2", "T3"]
    # Must NOT contain future turn T4 or sibling turn T5
    assert "T4" not in ancestor_ids
    assert "T5" not in ancestor_ids


def test_assign_anonymous_actor_ids():
    """Verify stable anonymous actor ID assignment."""
    tweets = get_sample_tree_tweets()
    actor_map = assign_anonymous_actor_ids(tweets, brand_name="SpotifyCares")
    
    assert actor_map["SpotifyCares"] == "SpotifyCares"
    assert actor_map["Cust_A"] == "Customer_1"
    assert actor_map["Cust_B"] == "Customer_2"


def test_build_model_context_payload():
    """Verify model context building payload structure."""
    tweets = get_sample_tree_tweets()
    ctx = build_model_context(tweets, target_tweet_id="T3", brand_name="SpotifyCares")
    
    assert ctx["root_tweet_id"] == "T1"
    assert ctx["target_tweet_id"] == "T3"
    assert ctx["root_customer_turn"]["tweet_id"] == "T1"
    assert ctx["target_customer_turn"]["tweet_id"] == "T3"
    assert len(ctx["ancestor_turns"]) == 3
    assert "Customer_1" in ctx["model_input_text"]
    assert "SpotifyCares" in ctx["model_input_text"]
    assert "(TARGET CUSTOMER INQUIRY)" in ctx["model_input_text"]
