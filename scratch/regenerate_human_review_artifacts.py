"""
scratch/regenerate_human_review_artifacts.py
=============================================
Regenerates the human review workbook and human_ratings.csv from frozen predictions:
  1. Uses the same 30 clusters (90 system replies) from frozen evaluation predictions.
  2. Includes actual historical inquiry and brand-reply text for each retrieved evidence case,
     or explicitly states that no evidence was used.
  3. Adds stable review IDs (e.g. REV-001 to REV-090) for importing ratings without matching by row position.
  4. Keeps system identity mapping in a separate file (results/phase6/system_identity_mapping.csv & .json).
  5. Leaves all human rating fields strictly blank.
  6. Verifies that all 90 replies match 100% between the workbook and human_ratings.csv.
"""

import json
import csv
from pathlib import Path
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

REPO_ROOT = Path("E:/Reply_agent")
PHASE5_DIR = REPO_ROOT / "results" / "phase5"
PHASE6_DIR = REPO_ROOT / "results" / "phase6"
GOLDEN_EVAL_PATH = REPO_ROOT / "golden_eval.jsonl"
KNOWLEDGE_V2_PATH = REPO_ROOT / "data" / "processed" / "v2" / "spotify_knowledge.jsonl"
KNOWLEDGE_V1_PATH = REPO_ROOT / "data" / "processed" / "spotify_knowledge.jsonl"
OLD_RATINGS_CSV = REPO_ROOT / "human_ratings.csv"

OUT_RATINGS_CSV = REPO_ROOT / "human_ratings.csv"
OUT_MAPPING_CSV = PHASE6_DIR / "system_identity_mapping.csv"
OUT_MAPPING_JSON = PHASE6_DIR / "system_identity_mapping.json"
OUT_XLSX_V1 = PHASE6_DIR / "reply_human_review_task.xlsx"
OUT_XLSX_V2 = PHASE6_DIR / "reply_human_review_task_v2.xlsx"
OUT_JSONL_V1 = PHASE6_DIR / "human_ratings_90.jsonl"
OUT_JSONL_V2 = PHASE6_DIR / "human_ratings_90_v2.jsonl"

SYSTEM_BLIND_MAP = {
    "baseline_0_majority": "System_Alpha",
    "baseline_1_rules": "System_Beta",
    "main_agent_v1": "System_Gamma",
}

def load_jsonl(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def main():
    print("Starting generation of human review artifacts...")
    
    # 1. Load Knowledge Base
    knowledge = {}
    for p in [KNOWLEDGE_V2_PATH, KNOWLEDGE_V1_PATH]:
        if p.exists():
            for row in load_jsonl(p):
                knowledge[row["example_id"]] = row
    print(f"Loaded {len(knowledge)} knowledge base entries.")

    # 2. Load Gold Eval records
    gold_records = {r["example_id"]: r for r in load_jsonl(GOLDEN_EVAL_PATH)}
    print(f"Loaded {len(gold_records)} gold eval records.")

    # 3. Load Frozen Predictions
    preds_b0 = {r["example_id"]: r for r in load_jsonl(PHASE5_DIR / "eval_predictions_baseline_0.jsonl")}
    preds_b1 = {r["example_id"]: r for r in load_jsonl(PHASE5_DIR / "eval_predictions_baseline_1.jsonl")}
    preds_main = {r["example_id"]: r for r in load_jsonl(PHASE5_DIR / "eval_predictions_main_agent.jsonl")}
    preds_by_system = {
        "baseline_0_majority": preds_b0,
        "baseline_1_rules": preds_b1,
        "main_agent_v1": preds_main,
    }

    # 4. Extract the 30 sampled clusters in exact order from human_ratings.csv
    df_old = pd.read_csv(OLD_RATINGS_CSV, dtype=str, keep_default_na=False)
    seen_clusters = []
    for eid in df_old["example_id"]:
        if eid not in seen_clusters:
            seen_clusters.append(eid)
    assert len(seen_clusters) == 30, f"Expected 30 unique clusters, found {len(seen_clusters)}"
    print(f"Identified {len(seen_clusters)} sampled clusters from existing human ratings.")

    # 5. Build 90 items with full evidence and stable review IDs
    rows = []
    system_mappings = []
    
    item_counter = 0
    system_order = ["baseline_0_majority", "baseline_1_rules", "main_agent_v1"]

    for c_idx, eid in enumerate(seen_clusters, 1):
        gold = gold_records[eid]
        customer_msg = gold.get("message", "")

        for sys_id in system_order:
            item_counter += 1
            review_id = f"REV-{item_counter:03d}"
            blinded_sys = SYSTEM_BLIND_MAP[sys_id]
            pred = preds_by_system[sys_id][eid]
            predicted_reply = pred.get("predicted_reply", "")

            # Formulate Evidence Text
            if sys_id == "baseline_0_majority":
                evidence_text = "No evidence was used (fixed majority baseline; no retrieval mechanism)."
            elif sys_id == "baseline_1_rules":
                evidence_text = "No evidence was used (deterministic heuristic rules; no retrieval mechanism)."
            elif sys_id == "main_agent_v1":
                src_ids = pred.get("retrieved_source_ids", [])
                if not src_ids:
                    evidence_text = "No evidence was used (no historical support exchange met the retrieval similarity threshold)."
                else:
                    evidence_blocks = []
                    for s_idx, sid in enumerate(src_ids, 1):
                        k_entry = knowledge.get(sid, {})
                        inquiry = k_entry.get("customer_text", "(Inquiry text unavailable)")
                        reply = k_entry.get("brand_reply_text", "(Brand reply text unavailable)")
                        evidence_blocks.append(
                            f"[Evidence Case {s_idx}: {sid}]\n"
                            f"Historical Customer Inquiry: \"{inquiry}\"\n"
                            f"Historical Brand Reply: \"{reply}\""
                        )
                    evidence_text = "\n\n".join(evidence_blocks)
            else:
                evidence_text = "No evidence was used."

            # Review item row (Blinded)
            row_data = {
                "review_id": review_id,
                "example_id": eid,
                "blinded_system_id": blinded_sys,
                "customer_message": customer_msg,
                "retrieved_evidence": evidence_text,
                "predicted_reply": predicted_reply,
                # Blank human fields
                "relevance_human": "",
                "grounding_human": "",
                "usefulness_human": "",
                "tone_human": "",
                "critical_error_human": "",
                "annotator_id": "",
                "notes": "",
            }
            rows.append(row_data)

            # Separate system identity mapping
            system_mappings.append({
                "review_id": review_id,
                "example_id": eid,
                "blinded_system_id": blinded_sys,
                "system_id": sys_id,
            })

    assert len(rows) == 90, f"Expected 90 rows, got {len(rows)}"
    assert len(system_mappings) == 90, f"Expected 90 mapping rows, got {len(system_mappings)}"

    # 6. Save separate system identity mapping
    print(f"Saving separate system identity mapping to {OUT_MAPPING_CSV} and {OUT_MAPPING_JSON}...")
    df_map = pd.DataFrame(system_mappings)
    df_map.to_csv(OUT_MAPPING_CSV, index=False, encoding="utf-8")
    with open(OUT_MAPPING_JSON, "w", encoding="utf-8") as f:
        json.dump(system_mappings, f, indent=2, ensure_ascii=False)

    # 7. Save human_ratings.csv (Blinded, with blank human fields and stable review_id)
    print(f"Saving regenerated human_ratings.csv to {OUT_RATINGS_CSV}...")
    df_ratings = pd.DataFrame(rows)
    df_ratings.to_csv(OUT_RATINGS_CSV, index=False, encoding="utf-8")

    # Also save JSONL copies
    with open(OUT_JSONL_V1, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(OUT_JSONL_V2, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 8. Build Excel Workbook
    print(f"Generating Excel review task workbooks: {OUT_XLSX_V1} and {OUT_XLSX_V2}...")
    wb = openpyxl.Workbook()
    
    # Sheet 1: Reply_Review_Task
    ws = wb.active
    ws.title = "Reply_Review_Task"
    ws.views.sheetView[0].showGridLines = True

    # Sheet 2: Rubric_Reference
    ref_ws = wb.create_sheet(title="Rubric_Reference")
    ref_ws.views.sheetView[0].showGridLines = True

    rubric_rows = [
        ("Dimension", "Scale", "Definition & Operational Criteria"),
        ("Relevance", "0", "Irrelevant: Reply does not address the customer inquiry or discusses unrelated topics."),
        ("Relevance", "1", "Partially Relevant: Touches on the customer topic but misses main problem or includes off-topic remarks."),
        ("Relevance", "2", "Fully Relevant: Directly and completely addresses the specific customer inquiry."),
        ("Grounding", "0", "Ungrounded: Makes claims contradicted by official policy, invents unverified information, or contradicts retrieved evidence."),
        ("Grounding", "1", "Partially Grounded: Plausible general support advice but lacks clear policy or evidence grounding."),
        ("Grounding", "2", "Fully Grounded: Strictly consistent with official Spotify support policy, public FAQs, or provided historical exchange evidence."),
        ("Usefulness", "0", "Not Useful: Generic evasion, circular non-help, or advice that cannot assist the customer."),
        ("Usefulness", "1", "Moderately Useful: Gives general guidance or diagnostic steps that require further customer effort."),
        ("Usefulness", "2", "Highly Useful: Clear, actionable resolution path, troubleshooting step, or appropriate specialist escalation."),
        ("Tone", "0", "Inappropriate: Rude, dismissive, robotic boilerplate, or hostile."),
        ("Tone", "1", "Acceptable: Neutral, somewhat impersonal, but polite."),
        ("Tone", "2", "Excellent: Empathetic, warm, professional, and branded customer care tone."),
        ("Critical_Error", "False", "No critical error: Compliant support behavior."),
        ("Critical_Error", "True", "Critical violation: Promises unauthorized refund, falsely claims server outage, promises backend edits, or unsafely auto-handles account security."),
    ]

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    spotify_green = PatternFill(start_color="1DB954", end_color="1DB954", fill_type="solid")
    dark_header = PatternFill(start_color="191414", end_color="191414", fill_type="solid")

    for r_idx, r_data in enumerate(rubric_rows, 1):
        for c_idx, val in enumerate(r_data, 1):
            cell = ref_ws.cell(r_idx, c_idx, val)
            if r_idx == 1:
                cell.font = header_font
                cell.fill = dark_header
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    ref_ws.column_dimensions["A"].width = 18
    ref_ws.column_dimensions["B"].width = 10
    ref_ws.column_dimensions["C"].width = 85

    headers = [
        "Review_ID",
        "Example_ID",
        "Blinded_System_ID",
        "Customer_Message",
        "Retrieved_Evidence",
        "Predicted_Reply",
        "Human_Relevance",      # 0, 1, 2
        "Human_Grounding",      # 0, 1, 2
        "Human_Usefulness",     # 0, 1, 2
        "Human_Tone",           # 0, 1, 2
        "Human_Critical_Error", # False, True
        "Annotator_ID",
        "Notes",
    ]

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, h)
        cell.font = header_font
        if col_idx <= 6:
            cell.fill = dark_header # Context columns
        else:
            cell.fill = spotify_green # Blank Human Input columns
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 28

    border_side = Side(border_style="thin", color="D9D9D9")
    row_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)

    for idx, r in enumerate(rows, 1):
        row_num = idx + 1
        ws.row_dimensions[row_num].height = 70

        ws.cell(row_num, 1, r["review_id"]).alignment = Alignment(horizontal="center", vertical="top")
        ws.cell(row_num, 2, r["example_id"]).alignment = Alignment(horizontal="center", vertical="top")
        ws.cell(row_num, 3, r["blinded_system_id"]).alignment = Alignment(horizontal="center", vertical="top")
        ws.cell(row_num, 4, r["customer_message"]).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws.cell(row_num, 5, r["retrieved_evidence"]).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws.cell(row_num, 6, r["predicted_reply"]).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        # Blank human review fields (Cols 7 to 13)
        for c in range(7, 14):
            cell = ws.cell(row_num, c, None)
            cell.alignment = Alignment(horizontal="center" if c < 12 else "left", vertical="top", wrap_text=True)
            cell.border = row_border

        for c in range(1, 7):
            ws.cell(row_num, c).border = row_border

    # Data Validations
    dv_012 = DataValidation(type="list", formula1='"0,1,2"', allow_blank=True)
    dv_bool = DataValidation(type="list", formula1='"False,True"', allow_blank=True)
    ws.add_data_validation(dv_012)
    ws.add_data_validation(dv_bool)
    dv_012.add("G2:J91")
    dv_bool.add("K2:K91")

    ws.column_dimensions["A"].width = 14  # Review_ID
    ws.column_dimensions["B"].width = 36  # Example_ID
    ws.column_dimensions["C"].width = 18  # Blinded_System_ID
    ws.column_dimensions["D"].width = 45  # Customer_Message
    ws.column_dimensions["E"].width = 60  # Retrieved_Evidence
    ws.column_dimensions["F"].width = 50  # Predicted_Reply
    ws.column_dimensions["G"].width = 16  # Human_Relevance
    ws.column_dimensions["H"].width = 16  # Human_Grounding
    ws.column_dimensions["I"].width = 16  # Human_Usefulness
    ws.column_dimensions["J"].width = 14  # Human_Tone
    ws.column_dimensions["K"].width = 18  # Human_Critical_Error
    ws.column_dimensions["L"].width = 16  # Annotator_ID
    ws.column_dimensions["M"].width = 30  # Notes

    wb.save(OUT_XLSX_V1)
    wb.save(OUT_XLSX_V2)
    print(f"Saved {OUT_XLSX_V1} and {OUT_XLSX_V2}")

    # 9. Comprehensive Verification across CSV and Workbook
    print("Verifying 1-to-1 match across human_ratings.csv and Excel workbook...")
    df_check_csv = pd.read_csv(OUT_RATINGS_CSV, dtype=str, keep_default_na=False)
    df_check_xlsx = pd.read_excel(OUT_XLSX_V1, dtype=str, keep_default_na=False)

    assert len(df_check_csv) == 90, f"CSV length is {len(df_check_csv)}, expected 90"
    assert len(df_check_xlsx) == 90, f"XLSX length is {len(df_check_xlsx)}, expected 90"

    for i in range(90):
        c_row = df_check_csv.iloc[i]
        x_row = df_check_xlsx.iloc[i]

        assert c_row["review_id"] == x_row["Review_ID"], f"Mismatch in review_id at row {i}"
        assert c_row["example_id"] == x_row["Example_ID"], f"Mismatch in example_id at row {i}"
        assert c_row["blinded_system_id"] == x_row["Blinded_System_ID"], f"Mismatch in Blinded_System_ID at row {i}"
        assert c_row["customer_message"] == x_row["Customer_Message"], f"Mismatch in Customer_Message at row {i}"
        assert c_row["retrieved_evidence"] == x_row["Retrieved_Evidence"], f"Mismatch in Retrieved_Evidence at row {i}"
        assert c_row["predicted_reply"] == x_row["Predicted_Reply"], f"Mismatch in Predicted_Reply at row {i}"

        # Check human rating columns are completely blank
        for col in ["relevance_human", "grounding_human", "usefulness_human", "tone_human", "critical_error_human", "annotator_id"]:
            assert c_row[col] == "", f"CSV column {col} at row {i} is not empty!"
        for col in ["Human_Relevance", "Human_Grounding", "Human_Usefulness", "Human_Tone", "Human_Critical_Error", "Annotator_ID"]:
            assert x_row[col] == "", f"XLSX column {col} at row {i} is not empty!"

    print("SUCCESS: All 90 replies match 100% across CSV and Excel workbooks!")
    print("System identity mapping is isolated in results/phase6/system_identity_mapping.csv and .json.")
    print("All human-rating columns remain 100% blank.")

if __name__ == "__main__":
    main()
