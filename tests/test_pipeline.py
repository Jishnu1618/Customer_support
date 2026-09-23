import pytest
from pathlib import Path
from src.retriever import TFIDFRetriever
from src.pipeline import MainAgentPipeline

KNOWLEDGE_PATH = Path("e:/Reply_agent/data/processed/v2/spotify_knowledge.jsonl")

@pytest.fixture(scope="module")
def retriever():
    return TFIDFRetriever(KNOWLEDGE_PATH)

@pytest.fixture
def pipeline(retriever):
    # use_semantic_fallback=False so tests run without downloading the model
    return MainAgentPipeline(retriever=retriever, system_id="main_agent_v1", use_semantic_fallback=False)

def test_retriever_returns_top_5_nonduplicates(retriever):
    results = retriever.retrieve("cannot log in password reset link not working", top_k=5)
    assert len(results) == 5
    ids = [r["example_id"] for r in results]
    assert len(set(ids)) == 5  # Non-duplicate IDs
    for r in results:
        assert "example_id" in r
        assert "customer_text" in r
        assert "brand_reply_text" in r
        assert "similarity_score" in r
        assert isinstance(r["similarity_score"], float)

def test_pipeline_classify_stage(pipeline):
    res = pipeline.classify("deleted my Facebook account and now cannot access my spotify account", "")
    assert res["classified_intent"] == "account_access"
    assert res["risk_signals"]["sensitive_security"] is True
    assert res["risk_signals"]["account_action"] is True

def test_pipeline_validate_stage(pipeline):
    draft_res = {"draft_reply": "Please visit spotify.com/reset", "cited_evidence_ids": ["SpotifyCares:100:100:99"]}
    evidence = [{"example_id": "SpotifyCares:100:100:99", "brand_reply_text": "You can reset your password at spotify.com/reset"}]
    val_res = pipeline.validate(draft_res, evidence, "account_access", {})
    assert val_res["is_valid"] is True
    assert len(val_res["validation_errors"]) == 0

def test_draft_uses_retrieved_brand_reply(pipeline):
    # similarity_score must be >= 0.25 (new threshold) to use evidence
    evidence = [{
        "example_id": "SpotifyCares:999:999:998",
        "similarity_score": 0.85,
        "brand_reply_text": "@[CUSTOMER_HANDLE] Try clearing cache in Settings > Storage and restart your phone. /CE"
    }]
    draft_res = pipeline.draft("my app is lagging", "", "technical_support", {}, evidence)
    assert draft_res["cited_evidence_ids"] == ["SpotifyCares:999:999:998"]
    # Reply should contain the cleaned advice wrapped by the formatter
    assert "clearing cache" in draft_res["draft_reply"].lower()
    assert "@[CUSTOMER_HANDLE]" not in draft_res["draft_reply"]
    assert "/CE" not in draft_res["draft_reply"]
    # Formatter should add an opener and closer
    reply = draft_res["draft_reply"]
    assert len(reply) > 30   # has opener + advice + closer

def test_draft_reflects_contradictory_evidence(pipeline):
    contradictory_evidence = [{
        "example_id": "SpotifyCares:555:555:554",
        "similarity_score": 0.90,
        "brand_reply_text": "Do not reinstall the app. Please reboot your Wi-Fi router instead."
    }]
    draft_res = pipeline.draft("music won't load", "", "technical_support", {}, contradictory_evidence)
    assert draft_res["cited_evidence_ids"] == ["SpotifyCares:555:555:554"]
    # Core advice from evidence should be in the reply
    assert "reboot" in draft_res["draft_reply"].lower() or "router" in draft_res["draft_reply"].lower() or "wi-fi" in draft_res["draft_reply"].lower()
    assert "clean reinstall" not in draft_res["draft_reply"].lower()


def test_draft_falls_back_to_template_below_threshold(pipeline):
    """Evidence below 0.25 threshold should NOT be used — fallback template used instead."""
    low_confidence_evidence = [{
        "example_id": "SpotifyCares:001:001:000",
        "similarity_score": 0.10,   # below 0.25 threshold
        "brand_reply_text": "Try reinstalling the Spotify app."
    }]
    draft_res = pipeline.draft("what is up with my account", "", "account_access", {}, low_confidence_evidence)
    # Should not cite the low-confidence evidence
    assert draft_res["cited_evidence_ids"] == []
    # Should use the fallback template (which references spotify.com/reset or support.spotify.com)
    assert "spotify.com" in draft_res["draft_reply"].lower() or "support" in draft_res["draft_reply"].lower()


def test_reply_formatter_produces_structured_output(pipeline):
    """_format_reply must produce opener + action + closer structure."""
    reply = pipeline._format_reply("technical_support", "Clear the Spotify cache in device settings.")
    assert "sorry" in reply.lower() or "issue" in reply.lower()   # opener present
    assert "cache" in reply.lower()                                 # core advice
    assert "device" in reply.lower() or "os" in reply.lower() or "reply" in reply.lower() or "continues" in reply.lower()  # closer
    assert len(reply.split()) >= 10                                  # substantive


def test_classify_returns_used_semantic_fallback_key(pipeline):
    """classify() result must always include 'used_semantic_fallback' key."""
    res = pipeline.classify("I cannot log in", "")
    assert "used_semantic_fallback" in res

def test_validate_rejects_unsupported_substantive_claims(pipeline):
    # Draft makes substantive claims (reinstall, cache) not supported in router-only evidence
    draft_res = {
        "draft_reply": "We recommend performing a clean reinstall of the app and clearing cache.",
        "cited_evidence_ids": ["SpotifyCares:777:777:776"]
    }
    evidence = [{
        "example_id": "SpotifyCares:777:777:776",
        "brand_reply_text": "Please check your Wi-Fi connection and reboot your router."
    }]
    val_res = pipeline.validate(draft_res, evidence, "technical_support", {})
    assert val_res["is_valid"] is False
    assert any("unsupported_substantive_claim" in err for err in val_res["validation_errors"])

def test_validate_rejects_contradictory_claims(pipeline):
    # Draft recommends reinstalling, but cited evidence explicitly says do not reinstall
    draft_res = {
        "draft_reply": "Please reinstall the application to fix this.",
        "cited_evidence_ids": ["SpotifyCares:888:888:887"]
    }
    evidence = [{
        "example_id": "SpotifyCares:888:888:887",
        "brand_reply_text": "Do not reinstall the app, this is a server-side bug."
    }]
    val_res = pipeline.validate(draft_res, evidence, "technical_support", {})
    assert val_res["is_valid"] is False
    assert any("contradictory_evidence_claim" in err for err in val_res["validation_errors"])

def test_pipeline_route_stage(pipeline):
    risk_signals = {"sensitive_security": True, "account_action": True}
    val_res = {"is_valid": True}
    route_res = pipeline.route("account_access", risk_signals, val_res, [])
    assert route_res["must_escalate"] is True
    assert route_res["decision"] == "escalate"
    assert "sensitive_security_request" in route_res["reason_code"]

def test_end_to_end_predict_pipeline(pipeline):
    record = {
        "example_id": "SpotifyCares:857985:857985:857984",
        "conversation_id": "857985",
        "message": "why AM to PM by Christina Milian is not available on US Spotify?!?",
        "prior_context": ""
    }
    pred = pipeline.predict(record)
    assert pred["example_id"] == "SpotifyCares:857985:857985:857984"
    assert pred["system_id"] == "main_agent_v1"
    assert pred["predicted_intent"] == "content_availability"
    assert isinstance(pred["predicted_must_escalate"], bool)
    assert len(pred["predicted_reply"]) > 0
    assert "intermediate_states" in pred
    assert "classify" in pred["intermediate_states"]
    assert "retrieve" in pred["intermediate_states"]
    assert "draft" in pred["intermediate_states"]
    assert "validate" in pred["intermediate_states"]
    assert "route" in pred["intermediate_states"]
