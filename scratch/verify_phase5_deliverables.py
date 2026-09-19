import json
from pathlib import Path

ROOT = Path("e:/Reply_agent")
RESULTS_DIR = ROOT / "results/phase5"

def verify_phase5():
    print("--- Phase 5 Comprehensive Verification Start ---")
    
    # 1. Check frozen_config.json
    config_path = RESULTS_DIR / "frozen_config.json"
    assert config_path.exists(), "frozen_config.json missing"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    assert "git_commit_hash" in cfg, "Missing git_commit_hash"
    assert "knowledge_corpus" in cfg and "sha256" in cfg["knowledge_corpus"], "Missing knowledge_corpus sha256"
    assert "taxonomy" in cfg and "retriever" in cfg, "Missing taxonomy or retriever config"
    print("[OK] 1. frozen_config.json verified!")

    # 2. Check retrieval_inspection_20.md
    insp_path = RESULTS_DIR / "retrieval_inspection_20.md"
    assert insp_path.exists(), "retrieval_inspection_20.md missing"
    insp_text = insp_path.read_text(encoding="utf-8")
    assert "20" in insp_text and "Useful Next Step?" in insp_text, "Invalid retrieval_inspection_20.md"
    print("[OK] 2. retrieval_inspection_20.md verified!")

    # 3. Check tuning_log.md
    tuning_path = RESULTS_DIR / "tuning_log.md"
    assert tuning_path.exists(), "tuning_log.md missing"
    tuning_text = tuning_path.read_text(encoding="utf-8")
    assert "Round 1" in tuning_text and "Round 2" in tuning_text and "Round 3" in tuning_text, "Invalid tuning_log.md"
    print("[OK] 3. tuning_log.md verified!")

    # 4. Check dev set predictions (50 records each)
    dev_files = [
        "dev_predictions_baseline_0.jsonl",
        "dev_predictions_baseline_1.jsonl",
        "dev_predictions_main_agent.jsonl"
    ]
    for fname in dev_files:
        fpath = RESULTS_DIR / fname
        assert fpath.exists(), f"Dev prediction file {fname} missing"
        records = [json.loads(line) for line in fpath.read_text(encoding="utf-8").strip().split("\n")]
        assert len(records) == 50, f"Expected 50 dev records in {fname}, got {len(records)}"
    print("[OK] 4. Dev predictions (50 records x 3 systems) verified!")

    # 5. Check eval set predictions (200 records each)
    eval_files = [
        "eval_predictions_baseline_0.jsonl",
        "eval_predictions_baseline_1.jsonl",
        "eval_predictions_main_agent.jsonl"
    ]
    required_eval_fields = [
        "example_id", "system_id", "predicted_intent", "predicted_must_escalate",
        "predicted_reply", "predicted_reason", "retrieved_source_ids", "runtime_ms"
    ]
    for fname in eval_files:
        fpath = RESULTS_DIR / fname
        assert fpath.exists(), f"Eval prediction file {fname} missing"
        records = [json.loads(line) for line in fpath.read_text(encoding="utf-8").strip().split("\n")]
        assert len(records) == 200, f"Expected 200 eval records in {fname}, got {len(records)}"
        for r in records:
            for field in required_eval_fields:
                assert field in r, f"Missing field {field} in {fname} record {r.get('example_id')}"
            assert isinstance(r["predicted_must_escalate"], bool)
    print("[OK] 5. Eval predictions (200 records x 3 systems) verified!")

    # 6. Check final report
    report_path = RESULTS_DIR / "phase5_final_report.md"
    assert report_path.exists(), "phase5_final_report.md missing"
    report_text = report_path.read_text(encoding="utf-8")
    assert "Main Agent Pipeline" in report_text and "Baseline 0" in report_text, "Invalid final report content"
    print("[OK] 6. phase5_final_report.md verified!")

    print("\nALL PHASE 5 DELIVERABLES COMPREHENSIVELY VERIFIED!")

if __name__ == "__main__":
    verify_phase5()
