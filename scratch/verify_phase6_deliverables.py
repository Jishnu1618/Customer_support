import json
from pathlib import Path

ROOT = Path("e:/Reply_agent")
RESULTS_DIR = ROOT / "results/phase6"

def verify_phase6():
    print("--- Phase 6 Comprehensive Verification Start ---")
    
    # 1. Check judge_rubric.md
    rubric_path = RESULTS_DIR / "judge_rubric.md"
    assert rubric_path.exists(), "judge_rubric.md missing"
    rubric_text = rubric_path.read_text(encoding="utf-8")
    assert "Frozen LLM Judge Rubric Specification" in rubric_text, "Invalid judge_rubric.md"
    print("[OK] 1. judge_rubric.md verified!")

    # 2. Check judge_predictions_600.jsonl
    preds_path = RESULTS_DIR / "judge_predictions_600.jsonl"
    assert preds_path.exists(), "judge_predictions_600.jsonl missing"
    judge_preds = [json.loads(line) for line in preds_path.read_text(encoding="utf-8").strip().split("\n")]
    assert len(judge_preds) == 600, f"Expected 600 judge prediction records, got {len(judge_preds)}"
    sys_counts = {}
    for r in judge_preds:
        s = r["system_id"]
        sys_counts[s] = sys_counts.get(s, 0) + 1
        assert "judge_scores" in r, "Missing judge_scores"
        assert "relevance" in r["judge_scores"]
        assert "critical_error" in r["judge_scores"]
    assert sys_counts.get("baseline_0_majority") == 200, f"Expected 200 for Baseline 0, got {sys_counts}"
    assert sys_counts.get("baseline_1_rules") == 200, f"Expected 200 for Baseline 1, got {sys_counts}"
    assert sys_counts.get("main_agent_v1") == 200, f"Expected 200 for Main Agent, got {sys_counts}"
    print(f"[OK] 2. judge_predictions_600.jsonl verified! System counts: {sys_counts}")

    # 3. Check human_ratings_90.jsonl
    human_path = RESULTS_DIR / "human_ratings_90.jsonl"
    assert human_path.exists(), "human_ratings_90.jsonl missing"
    human_ratings = [json.loads(line) for line in human_path.read_text(encoding="utf-8").strip().split("\n")]
    assert len(human_ratings) == 90, f"Expected 90 human rating records, got {len(human_ratings)}"
    h_msg_ids = set(r["example_id"] for r in human_ratings)
    assert len(h_msg_ids) == 30, f"Expected 30 unique messages in human audit, got {len(h_msg_ids)}"
    print("[OK] 3. human_ratings_90.jsonl verified!")

    # 4. Check judge_validation_agreement.md
    agree_path = RESULTS_DIR / "judge_validation_agreement.md"
    assert agree_path.exists(), "judge_validation_agreement.md missing"
    agree_text = agree_path.read_text(encoding="utf-8")
    assert "Linear-Weighted Cohen's Kappa" in agree_text, "Missing Kappa in agreement report"
    assert "Critical Error Flag Confusion Matrix" in agree_text, "Missing confusion matrix in agreement report"
    print("[OK] 4. judge_validation_agreement.md verified!")

    # 5. Check phase6_evaluation_report.md
    report_path = RESULTS_DIR / "phase6_evaluation_report.md"
    assert report_path.exists(), "phase6_evaluation_report.md missing"
    report_text = report_path.read_text(encoding="utf-8")
    assert "Overall System Performance (200 Messages)" in report_text, "Missing overall table in report"
    assert "Random Held-Out Pool (150 Messages)" in report_text, "Missing random pool table in report"
    assert "Feature Challenge Pool (50 Messages)" in report_text, "Missing challenge pool table in report"
    assert "Unsafe Automation Rate" in report_text, "Missing Unsafe Automation Rate in report"
    assert "Escalation Recall" in report_text, "Missing Escalation Recall in report"
    print("[OK] 5. phase6_evaluation_report.md verified!")

    print("\nALL PHASE 6 DELIVERABLES COMPREHENSIVELY VERIFIED!")

if __name__ == "__main__":
    verify_phase6()
