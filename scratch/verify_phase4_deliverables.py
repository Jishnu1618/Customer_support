import json
from pathlib import Path

ROOT = Path("e:/Reply_agent")
RESULTS_DIR = ROOT / "results/phase4"

def verify_phase4():
    print("--- Phase 4 Verification Start ---")
    
    b0_path = RESULTS_DIR / "baseline_0_dev_predictions.jsonl"
    b1_path = RESULTS_DIR / "baseline_1_dev_predictions.jsonl"
    report_path = RESULTS_DIR / "baseline_evaluation_report.md"
    
    assert b0_path.exists(), "baseline_0_dev_predictions.jsonl missing"
    assert b1_path.exists(), "baseline_1_dev_predictions.jsonl missing"
    assert report_path.exists(), "baseline_evaluation_report.md missing"
    
    b0_recs = [json.loads(line) for line in b0_path.read_text(encoding="utf-8").strip().split("\n")]
    b1_recs = [json.loads(line) for line in b1_path.read_text(encoding="utf-8").strip().split("\n")]
    
    assert len(b0_recs) == 50, f"Expected 50 Baseline 0 records, got {len(b0_recs)}"
    assert len(b1_recs) == 50, f"Expected 50 Baseline 1 records, got {len(b1_recs)}"
    
    required_fields = [
        "example_id", "system_id", "predicted_intent", "predicted_must_escalate",
        "predicted_reply", "predicted_reason", "retrieved_source_ids", "runtime_ms"
    ]
    
    for r in b0_recs:
        for field in required_fields:
            assert field in r, f"Missing field {field} in Baseline 0 record {r.get('example_id')}"
        assert r["system_id"] == "baseline_0_majority"
        assert r["predicted_must_escalate"] is True
        
    for r in b1_recs:
        for field in required_fields:
            assert field in r, f"Missing field {field} in Baseline 1 record {r.get('example_id')}"
        assert r["system_id"] == "baseline_1_rules"
        assert isinstance(r["retrieved_source_ids"], list)
        
    report_text = report_path.read_text(encoding="utf-8")
    assert "Baseline 0" in report_text and "Baseline 1" in report_text, "Missing model sections in report"
    assert "Ambiguous" in report_text and "Sensitive Security" in report_text, "Missing subset analysis in report"
    
    print("[OK] All Phase 4 Baseline deliverables verified successfully!")

if __name__ == "__main__":
    verify_phase4()
