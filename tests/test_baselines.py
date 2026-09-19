import pytest
from src.baselines import BaseReplyAgent, Baseline0MajorityAgent, Baseline1RuleAgent

@pytest.fixture
def sample_records():
    return [
        {
            "example_id": "SpotifyCares:857985:857985:857984",
            "conversation_id": "857985",
            "message": "why AM to PM by Christina Milian is not available on US Spotify?!?",
            "prior_context": ""
        },
        {
            "example_id": "SpotifyCares:2707737:2707737:2707736",
            "conversation_id": "2707737",
            "message": "deleted my Facebook account and now cannot access my spotify account. Help.",
            "prior_context": ""
        },
        {
            "example_id": "SpotifyCares:2032680:2032680:2032679",
            "conversation_id": "2032680",
            "message": "Sort out your Chrome web app @Spotify I'm trying to get through my working day here #glitchy",
            "prior_context": ""
        }
    ]

def test_baseline_0_interface_and_prediction(sample_records):
    agent = Baseline0MajorityAgent()
    assert isinstance(agent, BaseReplyAgent)
    
    preds = agent.predict_batch(sample_records)
    assert len(preds) == 3
    
    for p in preds:
        assert p["system_id"] == "baseline_0_majority"
        assert p["predicted_intent"] == "platform_and_regional"
        assert p["predicted_must_escalate"] is True
        assert "Thanks for reaching out" in p["predicted_reply"]
        assert p["predicted_reason"] == "fixed_majority_class_always_escalate"
        assert isinstance(p["retrieved_source_ids"], list)
        assert isinstance(p["runtime_ms"], float)

def test_baseline_1_interface_and_rule_predictions(sample_records):
    agent = Baseline1RuleAgent()
    assert isinstance(agent, BaseReplyAgent)
    
    preds = agent.predict_batch(sample_records)
    assert len(preds) == 3
    
    # Record 0: Licensing query -> content_availability
    assert preds[0]["predicted_intent"] == "content_availability"
    assert "KB-001-LICENSING" in preds[0]["retrieved_source_ids"]
    
    # Record 1: Facebook SSO deletion security issue -> account_access, must_escalate=True
    assert preds[1]["predicted_intent"] == "account_access"
    assert preds[1]["predicted_must_escalate"] is True
    assert "KB-003-ACCOUNT-RECOVERY" in preds[1]["retrieved_source_ids"]
    
    # Record 2: Chrome web player bug -> technical_support
    assert preds[2]["predicted_intent"] == "technical_support"
    assert "KB-002-TROUBLESHOOTING" in preds[2]["retrieved_source_ids"]
