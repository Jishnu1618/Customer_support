import json
import yaml
import pandas as pd
from pathlib import Path

ROOT = Path("e:/Reply_agent")

def verify_all():
    print("--- Phase 3 Verification Start ---")
    
    # 1. Validate intents.yaml
    intents_yaml_path = ROOT / "intents.yaml"
    assert intents_yaml_path.exists(), "intents.yaml missing"
    with open(intents_yaml_path, "r", encoding="utf-8") as f:
        intents_data = yaml.safe_load(f)
    assert len(intents_data["intents"]) == 8, f"Expected 8 intents, got {len(intents_data['intents'])}"
    for k, v in intents_data["intents"].items():
        assert "definition" in v, f"Missing definition in {k}"
        assert "exclusions" in v and len(v["exclusions"]) > 0, f"Missing exclusions in {k}"
        assert "examples" in v and len(v["examples"]) >= 2, f"Expected at least 2 examples in {k}, got {len(v['examples'])}"
    print("[OK] 1. intents.yaml validation PASSED!")

    # 2. Validate annotation_guidelines.md
    guidelines_path = ROOT / "annotation_guidelines.md"
    assert guidelines_path.exists(), "annotation_guidelines.md missing"
    guidelines_text = guidelines_path.read_text(encoding="utf-8")
    assert "1.0" in guidelines_text, "Missing version 1.0 in annotation_guidelines.md"
    print("[OK] 2. annotation_guidelines.md validation PASSED!")

    # 3. Validate dev_gold.jsonl
    dev_gold_path = ROOT / "dev_gold.jsonl"
    assert dev_gold_path.exists(), "dev_gold.jsonl missing"
    dev_records = [json.loads(line) for line in dev_gold_path.read_text(encoding="utf-8").strip().split("\n")]
    assert len(dev_records) == 50, f"Expected 50 dev records, got {len(dev_records)}"
    required_fields = [
        "example_id", "conversation_id", "subset", "message", "prior_context",
        "intent", "must_escalate", "reason", "required_elements", "forbidden_claims",
        "annotator", "guideline_version"
    ]
    for r in dev_records:
        for field in required_fields:
            assert field in r, f"Missing field {field} in dev record {r.get('example_id')}"
        assert r["subset"] == "dev", f"Expected subset 'dev', got {r['subset']}"
        assert isinstance(r["must_escalate"], bool), f"must_escalate must be bool in {r['example_id']}"
    print("[OK] 3. dev_gold.jsonl validation PASSED!")

    # 4. Validate golden_eval.jsonl
    golden_eval_path = ROOT / "golden_eval.jsonl"
    assert golden_eval_path.exists(), "golden_eval.jsonl missing"
    eval_records = [json.loads(line) for line in golden_eval_path.read_text(encoding="utf-8").strip().split("\n")]
    assert len(eval_records) == 200, f"Expected 200 eval records, got {len(eval_records)}"
    subsets = {}
    for r in eval_records:
        for field in required_fields:
            assert field in r, f"Missing field {field} in eval record {r.get('example_id')}"
        assert isinstance(r["must_escalate"], bool), f"must_escalate must be bool in {r['example_id']}"
        s = r["subset"]
        subsets[s] = subsets.get(s, 0) + 1
    assert subsets.get("random", 0) == 150, f"Expected 150 random records, got {subsets}"
    assert subsets.get("challenge", 0) == 50, f"Expected 50 challenge records, got {subsets}"
    print(f"[OK] 4. golden_eval.jsonl validation PASSED! Subsets breakdown: {subsets}")

    # 5. Validate sampling_notes.md
    sampling_notes_path = ROOT / "sampling_notes.md"
    assert sampling_notes_path.exists(), "sampling_notes.md missing"
    notes_text = sampling_notes_path.read_text(encoding="utf-8")
    assert "150" in notes_text and "50" in notes_text, "Missing sampling counts in sampling_notes.md"
    assert "Intra-Annotator Test-Retest Audit" in notes_text, "Missing audit log section in sampling_notes.md"
    print("[OK] 5. sampling_notes.md validation PASSED!")

    print("\nALL PHASE 3 DELIVERABLES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    verify_all()
