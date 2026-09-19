"""
Comprehensive Annotation Validation Script for Spotify Customer Support Reply Agent
Validates human-review workbooks, gold labels, dev labels, taxonomy compliance,
schema completeness, and partition isolation.
"""

import sys
import json
from pathlib import Path
import pandas as pd
import openpyxl

REPO_ROOT = Path(__file__).resolve().parent

def validate_all_annotations():
    print("================================================================================")
    print("                STARTING COMPREHENSIVE ANNOTATION VALIDATION                   ")
    print("================================================================================")
    
    # 1. Validate Taxonomy (intents.yaml & configs/intent_taxonomy.json)
    intents_yaml_path = REPO_ROOT / "intents.yaml"
    assert intents_yaml_path.exists(), "intents.yaml missing"
    
    # Parse YAML safely without external dependency if needed
    yaml_lines = intents_yaml_path.read_text(encoding="utf-8").splitlines()
    assert any("version: '1.0'" in line or 'version: "1.0"' in line or 'version: 1.0' in line for line in yaml_lines), "intents.yaml must be version 1.0"
    
    taxonomy_json_path = REPO_ROOT / "configs" / "intent_taxonomy.json"
    assert taxonomy_json_path.exists(), "configs/intent_taxonomy.json missing"
    with open(taxonomy_json_path, "r", encoding="utf-8") as f:
        tax_data = json.load(f)
    
    if isinstance(tax_data["intents"], list):
        valid_intents = {item["intent_id"] for item in tax_data["intents"]}
    else:
        valid_intents = set(tax_data["intents"].keys())
    assert len(valid_intents) == 8, f"Expected 8 intents, got {len(valid_intents)}: {valid_intents}"
    print(f"[OK] 1. Taxonomy Validated: 8 frozen intents {sorted(list(valid_intents))}")

    # 2. Validate Annotation Guidelines
    guidelines_path = REPO_ROOT / "annotation_guidelines.md"
    assert guidelines_path.exists(), "annotation_guidelines.md missing"
    g_text = guidelines_path.read_text(encoding="utf-8")
    assert "**Document Version:** 1.0 (Frozen Specification)" in g_text, "Missing v1.0 frozen header in guidelines"
    for intent in valid_intents:
        assert intent in g_text, f"Intent {intent} missing in annotation guidelines"
    print("[OK] 2. Annotation Guidelines Validated: Version 1.0 (Frozen Specification)")

    # 3. Validate Human Review Workbook (gold_human_review.xlsx)
    xlsx_path = REPO_ROOT / "gold_human_review.xlsx"
    assert xlsx_path.exists(), "gold_human_review.xlsx missing"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    assert "Gold_Human_Review" in wb.sheetnames, "Missing Gold_Human_Review sheet"
    assert "Taxonomy_Reference" in wb.sheetnames, "Missing Taxonomy_Reference sheet"
    ws = wb["Gold_Human_Review"]
    assert ws.max_row == 201, f"Expected 201 rows (1 header + 200 items), got {ws.max_row}"
    
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    expected_headers = [
        "Example_ID", "Evaluation_Subset", "Allowed_Prior_Context", "Target_Customer_Message",
        "Human_Intent", "Human_Handling_Decision", "Human_Handling_Reason",
        "Human_Required_Reply_Elements", "Human_Prohibited_Claims_Or_Actions",
        "Human_Needs_Clarification", "Human_Annotation_Confidence", "Annotator_ID", "Notes"
    ]
    assert headers[:13] == expected_headers, f"Header mismatch: got {headers[:13]}"

    xlsx_rows = {}
    annotators_found = set()
    for r in range(2, 202):
        eid = str(ws.cell(r, 1).value).strip()
        subset = str(ws.cell(r, 2).value).strip()
        intent = str(ws.cell(r, 5).value).strip()
        decision = str(ws.cell(r, 6).value).strip()
        reason = str(ws.cell(r, 7).value).strip()
        req_el = str(ws.cell(r, 8).value).strip()
        proh_el = str(ws.cell(r, 9).value).strip()
        needs_clar = str(ws.cell(r, 10).value).strip()
        conf = str(ws.cell(r, 11).value).strip()
        annotator = str(ws.cell(r, 12).value).strip()
        
        assert eid.startswith("SpotifyCares:"), f"Invalid example_id at row {r}: {eid}"
        assert subset in ("random", "challenge"), f"Invalid subset at row {r}: {subset}"
        assert intent in valid_intents, f"Invalid intent at row {r}: {intent}"
        assert decision in ("auto_handle", "escalate"), f"Invalid decision at row {r}: {decision}"
        assert len(reason) > 0, f"Empty reason at row {r}"
        assert len(req_el) > 0, f"Empty required elements at row {r}"
        assert len(proh_el) > 0, f"Empty prohibited claims at row {r}"
        assert needs_clar in ("True", "False"), f"Invalid needs_clarification at row {r}: {needs_clar}"
        assert conf in ("high", "medium", "low"), f"Invalid confidence at row {r}: {conf}"
        assert annotator == "Jishnu Roy", f"Expected human annotator 'Jishnu Roy' at row {r}, got '{annotator}'"
        annotators_found.add(annotator)
        xlsx_rows[eid] = {
            "subset": subset, "intent": intent, "decision": decision,
            "reason": reason, "req_el": req_el, "proh_el": proh_el,
            "needs_clar": needs_clar, "conf": conf, "annotator": annotator
        }
    
    assert len(xlsx_rows) == 200, f"Expected 200 unique rows in xlsx, got {len(xlsx_rows)}"
    print(f"[OK] 3. Gold Human Review Workbook Validated: 200 rows fully reviewed by {annotators_found}")

    # 4. Validate Gold Labels CSV (gold_labels.csv)
    csv_path = REPO_ROOT / "gold_labels.csv"
    assert csv_path.exists(), "gold_labels.csv missing"
    df_gold = pd.read_csv(csv_path, dtype=str)
    assert len(df_gold) == 200, f"Expected 200 rows in gold_labels.csv, got {len(df_gold)}"
    assert set(df_gold["annotator_id"].unique()) == {"Jishnu Roy"}, f"Unexpected annotator in gold_labels.csv: {df_gold['annotator_id'].unique()}"
    for _, row in df_gold.iterrows():
        eid = row["example_id"]
        assert eid in xlsx_rows, f"Example {eid} in CSV not found in XLSX"
        assert row["intent"] == xlsx_rows[eid]["intent"]
        assert row["handling_decision"] == xlsx_rows[eid]["decision"]
    print("[OK] 4. Gold Labels CSV Validated: 200 rows 100% consistent with human review workbook")

    # 5. Validate Golden Evaluation JSONL (golden_eval.jsonl)
    jsonl_path = REPO_ROOT / "golden_eval.jsonl"
    assert jsonl_path.exists(), "golden_eval.jsonl missing"
    with open(jsonl_path, "r", encoding="utf-8") as f:
        eval_records = [json.loads(line) for line in f if line.strip()]
    assert len(eval_records) == 200, f"Expected 200 records in golden_eval.jsonl, got {len(eval_records)}"
    
    eval_subsets = {}
    for r in eval_records:
        eid = r["example_id"]
        assert eid in xlsx_rows, f"Record {eid} not found in XLSX"
        assert r["intent"] == xlsx_rows[eid]["intent"]
        assert r["must_escalate"] == (xlsx_rows[eid]["decision"] == "escalate")
        assert r["annotator"] == "Jishnu Roy"
        assert r["guideline_version"] == "v1.0"
        s = r["subset"]
        eval_subsets[s] = eval_subsets.get(s, 0) + 1
    
    assert eval_subsets == {"random": 150, "challenge": 50}, f"Unexpected subset split: {eval_subsets}"
    print(f"[OK] 5. Golden Evaluation JSONL Validated: 200 records (150 random + 50 challenge), guideline v1.0")

    # 6. Validate Development Gold Labels (dev_labels.csv & dev_gold.jsonl)
    dev_csv_path = REPO_ROOT / "dev_labels.csv"
    assert dev_csv_path.exists(), "dev_labels.csv missing"
    df_dev = pd.read_csv(dev_csv_path, dtype=str)
    assert len(df_dev) == 50, f"Expected 50 rows in dev_labels.csv, got {len(df_dev)}"
    assert set(df_dev["annotator_id"].unique()) == {"human_annotator_1"}, (
        f"Development annotator must remain 'human_annotator_1' (automated baseline / not user-reviewed), got {df_dev['annotator_id'].unique()}"
    )

    dev_jsonl_path = REPO_ROOT / "dev_gold.jsonl"
    assert dev_jsonl_path.exists(), "dev_gold.jsonl missing"
    with open(dev_jsonl_path, "r", encoding="utf-8") as f:
        dev_records = [json.loads(line) for line in f if line.strip()]
    assert len(dev_records) == 50, f"Expected 50 records in dev_gold.jsonl, got {len(dev_records)}"
    for r in dev_records:
        assert r["annotator"] == "human_annotator_1"
        assert r["guideline_version"] == "v1.0"
        assert r["intent"] in valid_intents
        assert isinstance(r["must_escalate"], bool)
    print("[OK] 6. Development Set Validated: 50 records, correctly recorded as 'human_annotator_1' (unaltered)")

    # 7. Validate Partition & Manifest Integrity
    split_manifest_path = REPO_ROOT / "data" / "manifests" / "v2" / "split_manifest.jsonl"
    assert split_manifest_path.exists(), "v2 split_manifest.jsonl missing"
    with open(split_manifest_path, "r", encoding="utf-8") as f:
        split_entries = [json.loads(line) for line in f if line.strip()]
    
    parts = {}
    for entry in split_entries:
        p = entry["partition"]
        parts[p] = parts.get(p, 0) + 1
    assert parts == {"historical": 3000, "dev": 50, "eval_pool": 994, "excluded_earlier_dev": 6}, f"Unexpected partitions: {parts}"
    
    # Load evaluation pool groups
    eval_pool_path = REPO_ROOT / "data" / "processed" / "v2" / "eval_pool_inputs.jsonl"
    with open(eval_pool_path, "r", encoding="utf-8") as f:
        eval_pool_records = [json.loads(line) for line in f if line.strip()]
    assert len(eval_pool_records) == 994, f"Expected 994 records in eval pool, got {len(eval_pool_records)}"
    eval_pool_gids = {str(r["group_id"]) for r in eval_pool_records}
    
    gold_gids = {r["conversation_id"] for r in eval_records}
    dev_gids = {r["conversation_id"] for r in dev_records}
    assert len(gold_gids & dev_gids) == 0, f"Critical leakage: overlap between dev and gold: {gold_gids & dev_gids}"
    print(f"[OK] 7. Partition Isolation Validated: 0 overlap between dev ({len(dev_gids)}) and gold ({len(gold_gids)}); 994 clean eval pool records")

    # 8. Groups 120298 & 352469 and Historical Dev Contamination Audit Status
    assert "120298" not in gold_gids, "Contaminated group 120298 found in gold set"
    assert "352469" not in gold_gids, "Contaminated group 352469 found in gold set"
    assert "120298" not in eval_pool_gids, "Contaminated group 120298 found in eval pool"
    assert "352469" not in eval_pool_gids, "Contaminated group 352469 found in eval pool"
    
    # Verify all 6 contaminated groups are excluded from gold and eval pool
    bad_historical_dev_gids = {"120298", "1736480", "2165541", "2293459", "2873", "352469"}
    assert len(bad_historical_dev_gids & gold_gids) == 0, f"Historical dev leakage into gold: {bad_historical_dev_gids & gold_gids}"
    assert len(bad_historical_dev_gids & eval_pool_gids) == 0, f"Historical dev leakage into eval pool: {bad_historical_dev_gids & eval_pool_gids}"
    
    # Verify complete exclusion history (all 171 earlier restricted roots + clusters)
    ex_hist_path = REPO_ROOT / "results" / "phase2" / "correction2" / "exclusion_history.json"
    if ex_hist_path.exists():
        with open(ex_hist_path, "r", encoding="utf-8") as f:
            ex_data = json.load(f)
        all_restricted = set(str(g) for g in ex_data.get("all_restricted_roots", []))
        assert len(all_restricted & gold_gids) == 0, f"Historical restricted roots overlap with gold: {all_restricted & gold_gids}"
        assert len(all_restricted & eval_pool_gids) == 0, f"Historical restricted roots overlap with eval pool: {all_restricted & eval_pool_gids}"

    # Verify confirmed clean replacements are present in gold
    assert "462668" in gold_gids, "Replacement group 462668 missing from gold set"
    assert "1555406" in gold_gids, "Replacement group 1555406 missing from gold set"
    assert len(gold_gids) == 200, f"Expected 200 unique gold conversation IDs, got {len(gold_gids)}"
    print("[OK] 8. Contamination Audit Verified: Groups 120298 & 352469 (and all 6 historical dev groups) 100% excluded from gold and eval pool; clean replacements 462668 & 1555406 active")

    # 9. Validate Human Ratings Review Template & Preserved Synthetic Fixture
    ratings_csv_path = REPO_ROOT / "human_ratings.csv"
    assert ratings_csv_path.exists(), "human_ratings.csv missing"
    df_ratings = pd.read_csv(ratings_csv_path, dtype=str, keep_default_na=False)
    assert len(df_ratings) == 90, f"Expected 90 validation template rows, got {len(df_ratings)}"
    unique_msgs = df_ratings["example_id"].nunique()
    assert unique_msgs == 30, f"Expected 30 unique message clusters in validation set, got {unique_msgs}"
    # Verify human review columns: either validly completed OR blank pending review
    is_completed = (df_ratings["relevance_human"].str.strip() != "").all()
    if is_completed:
        for h_col in ["relevance_human", "grounding_human", "usefulness_human", "tone_human"]:
            assert df_ratings[h_col].isin(["0", "1", "2"]).all(), f"Invalid value in '{h_col}'"
        assert df_ratings["critical_error_human"].isin(["0", "1", "false", "true", "False", "True"]).all(), "Invalid critical error value"
        print(f"[OK] 9. Human Ratings Validated: 90 completed independent human ratings across {unique_msgs} clusters verified!")
    else:
        for h_col in ["relevance_human", "grounding_human", "usefulness_human", "tone_human", "critical_error_human", "annotator_id"]:
            assert (df_ratings[h_col] == "").all(), f"Human review column '{h_col}' must be empty pending human intervention"
        print(f"[OK] 9. Human Ratings Review Template Validated: 90 rows across {unique_msgs} clusters with blank human fields; synthetic fixture preserved")

    # 10. Validate Prepared Human Review Task Workbook
    task_wb_path = REPO_ROOT / "results" / "phase6" / "reply_human_review_task.xlsx"
    assert task_wb_path.exists(), "reply_human_review_task.xlsx missing"
    df_task = pd.read_excel(task_wb_path)
    assert len(df_task) == 90, f"Expected 90 review rows, got {len(df_task)}"
    assert df_task[["Human_Relevance", "Human_Grounding", "Human_Usefulness", "Human_Tone", "Human_Critical_Error", "Annotator_ID"]].isna().all().all(), "Human review task workbook must have blank rating fields pending human review"
    print(f"[OK] 10. Reply Human Review Task Workbook Validated: 90 blinded rows prepared with blank rating columns")

    print("================================================================================")
    print("           ALL ANNOTATION ARTIFACTS AND POLICIES VERIFIED SUCCESSFULLY!         ")
    print("================================================================================")
    return True

if __name__ == "__main__":
    validate_all_annotations()
