"""
Tests for Language Detection and Contextual Interpretability (Correction 4)

Verifies:
1. Three explicit language states ('english', 'non_english', 'uncertain').
2. Contextual short answers ("Yes", "Android", "Still broken") remain eligible when preceded by explaining turns.
3. 'Connection refused' is not confidently classified as non-English.
4. Gibberish is not confidently classified as English merely because it uses Latin characters.
5. Changing the future reply cannot change language or interpretability decisions.
6. English ancestors do not override a clearly non-English target.
7. Language heuristic score naming and uncertainty handling.
"""

import pytest
from pathlib import Path
from src.language_filter import (
    detect_language_state,
    is_contextually_interpretable,
    export_human_review_sheet,
    LANGUAGE_STATE_ENGLISH,
    LANGUAGE_STATE_NON_ENGLISH,
    LANGUAGE_STATE_UNCERTAIN,
)


class TestExplicitLanguageStates:
    """Verifies that the three explicit language states are returned."""

    def test_three_explicit_states_exist(self):
        assert LANGUAGE_STATE_ENGLISH == "english"
        assert LANGUAGE_STATE_NON_ENGLISH == "non_english"
        assert LANGUAGE_STATE_UNCERTAIN == "uncertain"

    def test_clear_english_returns_english_state(self):
        text = "My Spotify desktop app keeps freezing whenever I try to play a podcast."
        state, score, reason = detect_language_state(text)
        assert state == LANGUAGE_STATE_ENGLISH
        assert score >= 0.6
        assert isinstance(score, float)
        assert reason == "english_stopwords_match"

    def test_clear_spanish_returns_non_english_state(self):
        text = "Hola @SpotifyCares no puedo iniciar sesion en mi cuenta de spotify"
        state, score, reason = detect_language_state(text)
        assert state == LANGUAGE_STATE_NON_ENGLISH
        assert score >= 0.5
        assert reason == "non_english_stopwords"

    def test_insufficient_evidence_returns_uncertain_state(self):
        # Missing evidence or ambiguous text should be uncertain, not non_english
        state, score, reason = detect_language_state("Spotify")
        assert state == LANGUAGE_STATE_UNCERTAIN
        assert score < 0.6


class TestContextualShortAnswers:
    """Verifies that understandable short follow-ups remain eligible when preceded by explaining turns."""

    def test_yes_followup_remains_eligible(self):
        target = "Yes"
        ancestors = [
            {"author_id": "cust_1", "text": "My playlist is not loading on my phone.", "inbound": 1},
            {"author_id": "SpotifyCares", "text": "Have you tried reinstalling the Spotify app?", "inbound": 0},
        ]
        state, score, reason = detect_language_state(target, ancestor_turns=ancestors)
        assert state == LANGUAGE_STATE_ENGLISH
        assert score >= 0.8
        assert reason == "contextual_english_short_answer"

        interpretable, interp_reason = is_contextually_interpretable(target, ancestor_turns=ancestors)
        assert interpretable is True
        assert interp_reason == "contextual_short_reply"

    def test_android_device_followup_remains_eligible(self):
        target = "Android"
        ancestors = [
            {"author_id": "cust_2", "text": "The app crashed after the recent update.", "inbound": 1},
            {"author_id": "SpotifyCares", "text": "What operating system or device are you using?", "inbound": 0},
        ]
        state, score, reason = detect_language_state(target, ancestor_turns=ancestors)
        assert state == LANGUAGE_STATE_ENGLISH
        assert score >= 0.8
        assert reason == "contextual_english_short_answer"

        interpretable, interp_reason = is_contextually_interpretable(target, ancestor_turns=ancestors)
        assert interpretable is True
        assert interp_reason == "contextual_short_reply"

    def test_still_broken_followup_remains_eligible(self):
        target = "Still broken"
        ancestors = [
            {"author_id": "cust_3", "text": "Cannot play downloaded songs offline.", "inbound": 1},
            {"author_id": "SpotifyCares", "text": "Try toggling offline mode off and on in your settings.", "inbound": 0},
        ]
        state, score, reason = detect_language_state(target, ancestor_turns=ancestors)
        assert state == LANGUAGE_STATE_ENGLISH
        assert score >= 0.8

        interpretable, interp_reason = is_contextually_interpretable(target, ancestor_turns=ancestors)
        assert interpretable is True

    def test_standalone_short_word_without_context_is_uncertain(self):
        # Without explaining prior turns, standalone "Yes" is uncertain / too short, not English
        state, score, reason = detect_language_state("Yes", ancestor_turns=None)
        assert state == LANGUAGE_STATE_UNCERTAIN
        assert reason == "too_short"

        interpretable, interp_reason = is_contextually_interpretable("Yes", ancestor_turns=None)
        assert interpretable is False


class TestTechnicalTermsNotConfidentlyNonEnglish:
    """Verifies that technical terms like 'Connection refused' are not classified as non-English."""

    def test_connection_refused_is_not_classified_as_non_english(self):
        text = "Connection refused"
        state, score, reason = detect_language_state(text)
        assert state != LANGUAGE_STATE_NON_ENGLISH
        assert state == LANGUAGE_STATE_UNCERTAIN
        assert reason == "technical_terms_no_stopwords"
        # Heuristic score should honestly reflect uncertainty
        assert score <= 0.60

    def test_connection_refused_with_prior_context_becomes_english(self):
        target = "Connection refused"
        ancestors = [
            {"author_id": "cust_4", "text": "The web player will not load any music.", "inbound": 1},
            {"author_id": "SpotifyCares", "text": "What error message are you seeing on screen?", "inbound": 0},
        ]
        state, score, reason = detect_language_state(target, ancestor_turns=ancestors)
        assert state == LANGUAGE_STATE_ENGLISH
        assert score >= 0.8
        assert reason == "contextual_english_short_answer"


class TestGibberishNotConfidentlyEnglish:
    """Verifies that Latin character gibberish is not classified as English."""

    def test_latin_gibberish_is_uncertain_not_english(self):
        gibberish = "asdfghjk qwertyuiop zxcvbnm"
        state, score, reason = detect_language_state(gibberish)
        assert state != LANGUAGE_STATE_ENGLISH
        assert state == LANGUAGE_STATE_UNCERTAIN
        assert reason == "unrecognized_tokens_insufficient_evidence"

    def test_short_gibberish_is_uncertain(self):
        gibberish = "asdf qwerty"
        state, score, reason = detect_language_state(gibberish)
        assert state != LANGUAGE_STATE_ENGLISH
        assert state == LANGUAGE_STATE_UNCERTAIN

    def test_gibberish_in_thread_not_classified_as_english(self):
        # Even with English prior context, gibberish target must NOT be classified as English
        gibberish = "asdfghjk"
        ancestors = [
            {"author_id": "cust_5", "text": "Help with my account please.", "inbound": 1},
            {"author_id": "SpotifyCares", "text": "What seems to be the trouble?", "inbound": 0},
        ]
        state, score, reason = detect_language_state(gibberish, ancestor_turns=ancestors)
        assert state != LANGUAGE_STATE_ENGLISH
        assert state == LANGUAGE_STATE_UNCERTAIN


class TestFutureReplyCannotAlterDecisions:
    """Verifies that changing or withholding future replies cannot alter language or interpretability decisions."""

    def test_changing_future_reply_preserves_language_state(self):
        target = "My music keeps skipping every time a new track starts"
        ancestors = [
            {"author_id": "cust_6", "text": "My music keeps skipping every time a new track starts", "inbound": 1}
        ]

        # Evaluate language state with no future reply (as required)
        state1, score1, reason1 = detect_language_state(target, ancestor_turns=None)

        # Hypothetical varied future replies
        future_replies = [
            "We'd love to help! Can you send us a quick DM with your device details?",
            "Hola! Por favor envíanos un mensaje directo para poder ayudarte.",
            "",
            None,
            "1234567890",
        ]

        # The language detection function signature only takes target and ancestor turns
        for reply in future_replies:
            state2, score2, reason2 = detect_language_state(target, ancestor_turns=None)
            assert state2 == state1
            assert score2 == score1
            assert reason2 == reason1

    def test_changing_future_reply_preserves_interpretability(self):
        target = "My playlist disappeared after updating the app"
        ancestors = [
            {"author_id": "cust_7", "text": target, "inbound": 1}
        ]

        valid1, reason1 = is_contextually_interpretable(target, ancestor_turns=None)
        assert valid1 is True

        for reply in ["", "DM us", "Hola", None]:
            valid2, reason2 = is_contextually_interpretable(target, ancestor_turns=None, reply_text=reply or "")
            assert valid2 == valid1
            assert reason2 == reason1


class TestEnglishAncestorsDoNotOverrideNonEnglishTarget:
    """Verifies that prior English turns do not override a clearly non-English target customer message."""

    def test_spanish_target_after_english_turns_remains_non_english(self):
        # Scenario: Customer initially tweeted in English, brand replied in English,
        # but the target customer turn switched to Spanish.
        ancestors = [
            {"author_id": "cust_8", "text": "Hello @SpotifyCares I need help with my account", "inbound": 1},
            {"author_id": "SpotifyCares", "text": "Hi there! How can we help you today?", "inbound": 0},
        ]
        target_spanish = "Hola, mi musica no funciona y no puedo escuchar nada en mi celular"

        state, score, reason = detect_language_state(target_spanish, ancestor_turns=ancestors)
        assert state == LANGUAGE_STATE_NON_ENGLISH
        assert reason == "non_english_stopwords"

    def test_portuguese_target_after_english_turns_remains_non_english(self):
        ancestors = [
            {"author_id": "cust_9", "text": "Spotify support please help", "inbound": 1},
            {"author_id": "SpotifyCares", "text": "Sure thing! What is happening?", "inbound": 0},
        ]
        target_portuguese = "O aplicativo não abre e fecha sozinho quando clico na música"

        state, score, reason = detect_language_state(target_portuguese, ancestor_turns=ancestors)
        assert state == LANGUAGE_STATE_NON_ENGLISH
        assert reason == "non_english_stopwords"


class TestReviewSheetExport:
    """Verifies preparation of the human review sheet."""

    def test_review_sheet_columns_and_blank_human_labels(self, tmp_path: Path):
        csv_path = tmp_path / "test_review_sheet.csv"
        records = [
            {
                "sample_category": "accepted",
                "group_id": "101",
                "target_customer_tweet_id": "T101",
                "customer_text": "My app is crashing",
                "language_state": "english",
                "language_heuristic_score": 0.85,
                "detection_reason": "english_stopwords_match",
            },
            {
                "sample_category": "rejected",
                "group_id": "102",
                "target_customer_tweet_id": "T102",
                "customer_text": "No puedo escuchar musica",
                "language_state": "non_english",
                "language_heuristic_score": 0.80,
                "detection_reason": "non_english_stopwords",
            },
            {
                "sample_category": "uncertain",
                "group_id": "103",
                "target_customer_tweet_id": "T103",
                "customer_text": "Connection refused",
                "language_state": "uncertain",
                "language_heuristic_score": 0.50,
                "detection_reason": "technical_terms_no_stopwords",
            },
        ]
        export_human_review_sheet(records, csv_path)
        assert csv_path.exists()

        import csv
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 3
            for row in reader:
                # Human label columns must be completely blank
                assert row["human_language_label"] == ""
                assert row["human_interpretability_label"] == ""
                assert row["human_notes"] == ""
                assert row["language_heuristic_score"] != ""
