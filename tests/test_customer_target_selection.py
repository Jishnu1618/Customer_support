"""
Tests for Correction 3: Correct and Reproducible Customer-Target Selection

Tests required:
1. Another brand's outbound message cannot become a customer target.
2. Reordering database insertion produces the same selected examples.
3. An invalid first candidate does not hide a valid later candidate.
4. Multiple replies to the same customer produce a stable selection.
"""

import sqlite3
import pytest
from typing import List, Dict, Any

from src.prepare_phase2_dataset import extract_phase2_candidates, BRAND_NAME


def create_test_db() -> sqlite3.Connection:
    """Creates an in-memory SQLite database with TWCS schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE tweets (
            tweet_id TEXT PRIMARY KEY,
            author_id TEXT NOT NULL,
            inbound INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            text TEXT NOT NULL,
            response_tweet_id TEXT,
            in_response_to_tweet_id TEXT
        );
    """)
    cursor.execute("CREATE INDEX idx_in_response_to ON tweets(in_response_to_tweet_id);")
    conn.commit()
    return conn


def insert_tweets(conn: sqlite3.Connection, tweets: List[Dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO tweets (tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id)
        VALUES (:tweet_id, :author_id, :inbound, :created_at, :text, :response_tweet_id, :in_response_to_tweet_id)
    """, tweets)
    conn.commit()


class TestCustomerTargetSelection:
    """Tests ensuring customer target selection is correct, deterministic, and reproducible."""

    def test_another_brand_outbound_cannot_become_customer_target(self):
        """
        Verify that another brand's outbound message (inbound=0, author_id='AppleSupport')
        cannot be selected as a customer target, even if Spotify replied to it.
        """
        conn = create_test_db()
        tweets = [
            # Customer root inquiry
            {
                "tweet_id": "101",
                "author_id": "cust_1",
                "inbound": 1,
                "created_at": "Tue Nov 07 10:00:00 +0000 2017",
                "text": "@SpotifyCares @AppleSupport My Spotify app is crashing on my new iPhone",
                "response_tweet_id": "102,103",
                "in_response_to_tweet_id": None,
            },
            # Another brand's outbound reply (inbound=0, author_id='AppleSupport')
            {
                "tweet_id": "102",
                "author_id": "AppleSupport",
                "inbound": 0,
                "created_at": "Tue Nov 07 10:02:00 +0000 2017",
                "text": "@cust_1 @SpotifyCares Have you checked iOS settings for available updates?",
                "response_tweet_id": "104",
                "in_response_to_tweet_id": "101",
            },
            # Spotify reply directly to customer
            {
                "tweet_id": "103",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Tue Nov 07 10:03:00 +0000 2017",
                "text": "@cust_1 Let's help! Does this happen when opening a specific playlist?",
                "response_tweet_id": None,
                "in_response_to_tweet_id": "101",
            },
            # Spotify reply to AppleSupport's tweet (brand-to-brand)
            {
                "tweet_id": "104",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Tue Nov 07 10:04:00 +0000 2017",
                "text": "@AppleSupport Thanks for looping in, we are investigating with the user.",
                "response_tweet_id": None,
                "in_response_to_tweet_id": "102",
            },
        ]
        insert_tweets(conn, tweets)
        cursor = conn.cursor()

        candidates, exclusions, _ = extract_phase2_candidates(cursor, review_excluded_roots=set())
        conn.close()

        # Exactly 1 candidate extracted for group 101
        assert len(candidates) == 1
        cand = candidates[0]
        # Target customer tweet MUST be the inbound customer tweet (101), NEVER AppleSupport (102)
        assert cand["target_customer_tweet_id"] == "101"
        assert cand["selected_brand_reply_tweet_id"] == "103"
        assert "AppleSupport" not in cand["example_id"]

    def test_reordering_database_insertion_produces_same_selection(self):
        """
        Inserting the same set of tweets in completely different orders into SQLite
        must produce identical selected examples, customer tweet IDs, and reply tweet IDs.
        """
        tweets_order1 = [
            {
                "tweet_id": "201",
                "author_id": "cust_2",
                "inbound": 1,
                "created_at": "Wed Nov 08 12:00:00 +0000 2017",
                "text": "@SpotifyCares My offline songs refuse to sync on my Android phone",
                "response_tweet_id": "202",
                "in_response_to_tweet_id": None,
            },
            {
                "tweet_id": "202",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Wed Nov 08 12:05:00 +0000 2017",
                "text": "@cust_2 Can you try clearing your app cache and checking again?",
                "response_tweet_id": "203",
                "in_response_to_tweet_id": "201",
            },
            {
                "tweet_id": "203",
                "author_id": "cust_2",
                "inbound": 1,
                "created_at": "Wed Nov 08 12:10:00 +0000 2017",
                "text": "@SpotifyCares I cleared the cache and restarted but the tracks still fail to download",
                "response_tweet_id": "204",
                "in_response_to_tweet_id": "202",
            },
            {
                "tweet_id": "204",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Wed Nov 08 12:15:00 +0000 2017",
                "text": "@cust_2 Got it. Could you send us your Spotify version and device model?",
                "response_tweet_id": None,
                "in_response_to_tweet_id": "203",
            },
        ]

        # Order 2: Reverse/Scramble insertion order
        tweets_order2 = [tweets_order1[3], tweets_order1[0], tweets_order1[2], tweets_order1[1]]

        conn1 = create_test_db()
        insert_tweets(conn1, tweets_order1)
        cands1, _, _ = extract_phase2_candidates(conn1.cursor(), review_excluded_roots=set())
        conn1.close()

        conn2 = create_test_db()
        insert_tweets(conn2, tweets_order2)
        cands2, _, _ = extract_phase2_candidates(conn2.cursor(), review_excluded_roots=set())
        conn2.close()

        assert len(cands1) == 1
        assert len(cands2) == 1

        cand1 = cands1[0]
        cand2 = cands2[0]

        assert cand1["example_id"] == cand2["example_id"]
        assert cand1["target_customer_tweet_id"] == cand2["target_customer_tweet_id"]
        assert cand1["selected_brand_reply_tweet_id"] == cand2["selected_brand_reply_tweet_id"]
        assert cand1["model_input_text"] == cand2["model_input_text"]

    def test_invalid_first_candidate_does_not_hide_valid_later_candidate(self):
        """
        If the earliest customer turn in a thread is ineligible (e.g. non-English),
        a subsequent eligible customer turn in the same thread must be selected,
        retaining the conversation group instead of discarding it.
        """
        conn = create_test_db()
        tweets = [
            # Turn 1: Spanish inquiry (non-English -> ineligible)
            {
                "tweet_id": "301",
                "author_id": "cust_3",
                "inbound": 1,
                "created_at": "Thu Nov 09 08:00:00 +0000 2017",
                "text": "@SpotifyCares hola no puedo escuchar musica con mi cuenta por favor ayuda",
                "response_tweet_id": "302",
                "in_response_to_tweet_id": None,
            },
            # Brand reply to turn 1
            {
                "tweet_id": "302",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Thu Nov 09 08:05:00 +0000 2017",
                "text": "@cust_3 Hola! Nos puedes dar mas detalles sobre lo que sucede?",
                "response_tweet_id": "303",
                "in_response_to_tweet_id": "301",
            },
            # Turn 2: Customer switches to English (eligible!)
            {
                "tweet_id": "303",
                "author_id": "cust_3",
                "inbound": 1,
                "created_at": "Thu Nov 09 08:10:00 +0000 2017",
                "text": "@SpotifyCares I mean every song I play pauses after five seconds on my iPad",
                "response_tweet_id": "304",
                "in_response_to_tweet_id": "302",
            },
            # Brand reply to turn 2
            {
                "tweet_id": "304",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Thu Nov 09 08:15:00 +0000 2017",
                "text": "@cust_3 Thanks for explaining! Have you tried restarting your iPad and testing?",
                "response_tweet_id": None,
                "in_response_to_tweet_id": "303",
            },
        ]
        insert_tweets(conn, tweets)
        cursor = conn.cursor()

        candidates, exclusions, _ = extract_phase2_candidates(cursor, review_excluded_roots=set())
        conn.close()

        # The group must NOT be excluded as non-English; Turn 2 should be selected!
        assert len(candidates) == 1
        cand = candidates[0]
        assert cand["group_id"] == "301"
        assert cand["target_customer_tweet_id"] == "303"
        assert cand["selected_brand_reply_tweet_id"] == "304"

    def test_multiple_replies_to_same_customer_produce_stable_selection(self):
        """
        When a customer inquiry receives multiple replies from SpotifyCares,
        the selection must stably and deterministically pick the earliest reply.
        """
        tweets_order_a = [
            {
                "tweet_id": "401",
                "author_id": "cust_4",
                "inbound": 1,
                "created_at": "Fri Nov 10 14:00:00 +0000 2017",
                "text": "@SpotifyCares Cannot find the discover weekly playlist on my desktop app",
                "response_tweet_id": "402,403",
                "in_response_to_tweet_id": None,
            },
            # Earlier reply
            {
                "tweet_id": "402",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Fri Nov 10 14:02:00 +0000 2017",
                "text": "@cust_4 Hey! Look under 'Made For You' in your left sidebar.",
                "response_tweet_id": None,
                "in_response_to_tweet_id": "401",
            },
            # Later reply
            {
                "tweet_id": "403",
                "author_id": "SpotifyCares",
                "inbound": 0,
                "created_at": "Fri Nov 10 14:05:00 +0000 2017",
                "text": "@cust_4 Also make sure your desktop app is updated to the latest build.",
                "response_tweet_id": None,
                "in_response_to_tweet_id": "401",
            },
        ]

        # Order B: Insert later reply before earlier reply
        tweets_order_b = [tweets_order_a[0], tweets_order_a[2], tweets_order_a[1]]

        conn_a = create_test_db()
        insert_tweets(conn_a, tweets_order_a)
        cands_a, _, _ = extract_phase2_candidates(conn_a.cursor(), review_excluded_roots=set())
        conn_a.close()

        conn_b = create_test_db()
        insert_tweets(conn_b, tweets_order_b)
        cands_b, _, _ = extract_phase2_candidates(conn_b.cursor(), review_excluded_roots=set())
        conn_b.close()

        assert len(cands_a) == 1
        assert len(cands_b) == 1

        # Both must select reply 402 (the earlier reply by timestamp / lowest ID)
        assert cands_a[0]["selected_brand_reply_tweet_id"] == "402"
        assert cands_b[0]["selected_brand_reply_tweet_id"] == "402"
        assert cands_a[0]["example_id"] == cands_b[0]["example_id"]
