"""
tests/test_phase6.py — Phase 6 metric and LLM judge unit tests.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluate import wilson_ci, calculate_linear_weighted_kappa


# ---------------------------------------------------------------------------
# Metric tests (unchanged)
# ---------------------------------------------------------------------------

def test_wilson_ci():
    p, low, high = wilson_ci(50, 100)
    assert p == 0.5
    assert 0.40 <= low <= 0.42
    assert 0.58 <= high <= 0.60

    p0, low0, _ = wilson_ci(0, 50)
    assert p0 == 0.0
    assert low0 == 0.0

    p1, _, high1 = wilson_ci(50, 50)
    assert p1 == 1.0
    assert high1 == 1.0


def test_calculate_linear_weighted_kappa_perfect_agreement():
    r1 = [2, 1, 0, 2, 1, 0, 2, 2, 1, 0]
    r2 = [2, 1, 0, 2, 1, 0, 2, 2, 1, 0]
    exact_acc, kappa = calculate_linear_weighted_kappa(r1, r2, min_val=0, max_val=2)
    assert exact_acc == 1.0
    assert kappa == 1.0


def test_calculate_linear_weighted_kappa_partial_agreement():
    r1 = [2, 2, 1, 0, 2]
    r2 = [2, 1, 1, 0, 2]  # 1 off by 1
    exact_acc, kappa = calculate_linear_weighted_kappa(r1, r2, min_val=0, max_val=2)
    assert exact_acc == 0.8  # 4/5
    assert kappa > 0.6  # Linear weighting partial credit given


# ---------------------------------------------------------------------------
# LLM Judge unit tests
# ---------------------------------------------------------------------------

VALID_LLM_RESPONSE = json.dumps({
    "relevance": 2,
    "relevance_rationale": "Directly addresses the login issue.",
    "grounding": 1,
    "grounding_rationale": "Generic advice; no official URL cited.",
    "usefulness": 1,
    "usefulness_rationale": "Provides troubleshooting steps without a direct link.",
    "tone": 2,
    "tone_rationale": "Warm and empathetic.",
    "critical_error": False,
    "critical_error_details": {
        "unverified_refund_claim": False,
        "unverified_outage_claim": False,
        "unauthorized_account_edit_claim": False,
        "unsafe_automation_routing": False,
    },
    "critical_error_rationale": "No critical errors detected.",
})


def _make_judge(tmp_path: Path, mock_response: str = VALID_LLM_RESPONSE):
    """Construct an LLMRubricJudge with real rubric/prompt paths but mocked LLM calls."""
    # Ensure rubric and prompt files exist (use real paths from project)
    from llm_judge import LLMRubricJudge, RUBRIC_PATH, PROMPT_PATH

    if not RUBRIC_PATH.exists():
        pytest.skip(f"Rubric not found at {RUBRIC_PATH}")
    if not PROMPT_PATH.exists():
        pytest.skip(f"Prompt not found at {PROMPT_PATH}")

    cache_path = tmp_path / "test_cache.jsonl"
    judge = LLMRubricJudge(cache_path=cache_path)
    return judge


def test_llm_judge_returns_correct_schema(tmp_path):
    """LLMRubricJudge must return all required fields with correct types on success."""
    judge = _make_judge(tmp_path)

    with patch.object(judge, "_get_llm_client") as mock_client_getter:
        mock_client = MagicMock()
        mock_client.generate_reply.return_value = VALID_LLM_RESPONSE
        mock_client_getter.return_value = mock_client

        result = judge.evaluate_reply(
            customer_message="My Spotify app keeps crashing.",
            predicted_intent="technical_support",
            predicted_must_escalate=False,
            predicted_reply="Try a clean reinstall of the app.",
            gold_must_escalate=False,
        )

    # Judge type must be llm, NOT heuristic
    assert result["judge_type"] == "llm", f"Expected judge_type=llm, got {result['judge_type']}"

    # All required scores present with correct types
    for field in ["relevance", "grounding", "usefulness", "tone"]:
        assert field in result, f"Missing field: {field}"
        assert isinstance(result[field], int), f"{field} must be int"
        assert result[field] in (0, 1, 2), f"{field} must be 0, 1, or 2"
    assert "critical_error" in result
    assert isinstance(result["critical_error"], bool)

    # Provenance fields present
    assert result.get("model_id"), "model_id must be present"
    assert result.get("rubric_sha256"), "rubric_sha256 must be present"
    assert result.get("prompt_version") in ("v1.0", "v2.0"), \
        f"prompt_version must be a known valid version, got {result.get('prompt_version')!r}"
    assert result.get("cache_key"), "cache_key must be present"


def test_llm_judge_records_failure_not_substitutes(tmp_path):
    """On LLM call failure, must record failure — must NOT substitute heuristic scores."""
    judge = _make_judge(tmp_path)

    with patch.object(judge, "_get_llm_client") as mock_client_getter:
        mock_client = MagicMock()
        mock_client.generate_reply.side_effect = RuntimeError("API timeout")
        mock_client_getter.return_value = mock_client

        result = judge.evaluate_reply(
            customer_message="My Spotify app keeps crashing.",
            predicted_intent="technical_support",
            predicted_must_escalate=False,
            predicted_reply="Try a clean reinstall of the app.",
            gold_must_escalate=False,
        )

    # Must be flagged as failure
    assert result.get("llm_failure") is True, "llm_failure must be True on API error"
    assert result.get("failure_reason"), "failure_reason must be populated"

    # Must NOT contain heuristic substitution scores
    assert "relevance" not in result, "relevance must NOT be populated on failure"
    assert "grounding" not in result, "grounding must NOT be populated on failure"
    assert result.get("judge_type") == "llm", "judge_type must still be 'llm' (not 'heuristic')"


def test_llm_judge_records_parse_failure_not_substitutes(tmp_path):
    """On malformed JSON response, must record parse failure — must NOT substitute heuristic scores."""
    judge = _make_judge(tmp_path)

    with patch.object(judge, "_get_llm_client") as mock_client_getter:
        mock_client = MagicMock()
        mock_client.generate_reply.return_value = "Sorry, I cannot provide a JSON response."
        mock_client_getter.return_value = mock_client

        result = judge.evaluate_reply(
            customer_message="My Spotify app keeps crashing.",
            predicted_intent="technical_support",
            predicted_must_escalate=False,
            predicted_reply="Try a clean reinstall of the app.",
            gold_must_escalate=False,
        )

    assert result.get("llm_failure") is True, "llm_failure must be True on parse error"
    assert result.get("failure_reason"), "failure_reason must be populated"
    assert "relevance" not in result, "relevance must NOT be populated on parse failure"


def test_llm_judge_records_rubric_sha256(tmp_path):
    """rubric_sha256 must be non-empty and match the frozen rubric file."""
    from llm_judge import RUBRIC_PATH, _sha256

    judge = _make_judge(tmp_path)
    assert judge.rubric_sha256, "rubric_sha256 must be non-empty"
    # Use the same text-based hash as the judge (_sha256 reads as UTF-8 text)
    expected = _sha256(RUBRIC_PATH.read_text(encoding="utf-8"))
    assert judge.rubric_sha256 == expected, "rubric_sha256 must match actual rubric file"


def test_llm_judge_cache_hit_on_second_call(tmp_path):
    """Second identical call must be served from cache without making another LLM call."""
    judge = _make_judge(tmp_path)
    call_count = {"n": 0}

    def counting_generate(**kwargs):
        call_count["n"] += 1
        return VALID_LLM_RESPONSE

    with patch.object(judge, "_get_llm_client") as mock_client_getter:
        mock_client = MagicMock()
        mock_client.generate_reply.side_effect = lambda **kwargs: (
            call_count.__setitem__("n", call_count["n"] + 1) or VALID_LLM_RESPONSE
        )
        mock_client_getter.return_value = mock_client

        kwargs = dict(
            customer_message="My Spotify app keeps crashing.",
            predicted_intent="technical_support",
            predicted_must_escalate=False,
            predicted_reply="Try a clean reinstall of the app.",
            gold_must_escalate=False,
        )

        r1 = judge.evaluate_reply(**kwargs)
        r2 = judge.evaluate_reply(**kwargs)

    assert r1.get("from_cache") is False, "First call must not be from cache"
    assert r2.get("from_cache") is True, "Second identical call must be from cache"


def test_llm_judge_stale_cache_rejected(tmp_path):
    """Cache entry built with one rubric must be rejected when rubric hash changes."""
    from llm_judge import LLMRubricJudge, PROMPT_PATH

    # Create a temporary rubric (simulates rubric v1)
    fake_rubric = tmp_path / "rubric_v1.md"
    fake_rubric.write_text("# Rubric v1\nScore everything 2.", encoding="utf-8")

    cache_path = tmp_path / "test_cache.jsonl"

    # Judge 1 — uses fake rubric v1, populates cache
    judge1 = LLMRubricJudge.__new__(LLMRubricJudge)
    judge1.provider = "groq"
    judge1.model = "compound"
    judge1.model_id = "groq/compound"
    judge1.cache_path = cache_path
    judge1.rubric_text = fake_rubric.read_text(encoding="utf-8")
    judge1.prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    from llm_judge import _sha256
    judge1.rubric_sha256 = _sha256(judge1.rubric_text)
    judge1.prompt_sha256 = _sha256(judge1.prompt_template)
    judge1._cache = {}
    judge1._llm_client = None

    with patch.object(judge1, "_get_llm_client") as mock_getter:
        mock_client = MagicMock()
        mock_client.generate_reply.return_value = VALID_LLM_RESPONSE
        mock_getter.return_value = mock_client

        judge1.evaluate_reply(
            customer_message="Test message.",
            predicted_intent="technical_support",
            predicted_must_escalate=False,
            predicted_reply="Try reinstalling.",
            gold_must_escalate=False,
        )

    # Judge 2 — uses DIFFERENT rubric (simulates rubric v2), loads same cache
    # The cache entry should be INVALID because rubric_sha256 differs
    from llm_judge import RUBRIC_PATH
    judge2 = LLMRubricJudge(cache_path=cache_path)  # loads real rubric

    # real rubric sha differs from fake rubric sha
    assert judge2.rubric_sha256 != judge1.rubric_sha256, "Rubric SHAs must differ"

    # Judge 2 must not find a valid cache entry for the same inputs
    with patch.object(judge2, "_get_llm_client") as mock_getter2:
        mock_client2 = MagicMock()
        mock_client2.generate_reply.return_value = VALID_LLM_RESPONSE
        mock_getter2.return_value = mock_client2

        r2 = judge2.evaluate_reply(
            customer_message="Test message.",
            predicted_intent="technical_support",
            predicted_must_escalate=False,
            predicted_reply="Try reinstalling.",
            gold_must_escalate=False,
        )

    # r2 must be a fresh call (cache_key will differ because rubric_sha256 changed)
    assert r2.get("from_cache") is False, "Cache must be rejected when rubric changes"
    assert r2.get("judge_type") == "llm"


def test_llm_judge_interface_matches_heuristic_keys(tmp_path):
    """Successful LLM judge result must include all keys that heuristic judge produces."""
    from judge import RubricJudge

    heuristic = RubricJudge()
    h_result = heuristic.evaluate_reply(
        customer_message="App is broken.",
        predicted_intent="technical_support",
        predicted_must_escalate=False,
        predicted_reply="Please reinstall the app.",
        gold_must_escalate=False,
    )
    required_keys = {"relevance", "grounding", "usefulness", "tone", "critical_error"}
    assert required_keys.issubset(set(h_result.keys())), "Heuristic missing expected keys"

    judge = _make_judge(tmp_path)
    with patch.object(judge, "_get_llm_client") as mock_client_getter:
        mock_client = MagicMock()
        mock_client.generate_reply.return_value = VALID_LLM_RESPONSE
        mock_client_getter.return_value = mock_client

        llm_result = judge.evaluate_reply(
            customer_message="App is broken.",
            predicted_intent="technical_support",
            predicted_must_escalate=False,
            predicted_reply="Please reinstall the app.",
            gold_must_escalate=False,
        )

    assert required_keys.issubset(set(llm_result.keys())), (
        f"LLM judge missing keys that heuristic has: {required_keys - set(llm_result.keys())}"
    )
