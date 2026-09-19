"""
scratch/rebuild_reply_review_workbook.py
========================================
Regenerates the human reply-rating workbook with all material required for
independent annotation:
  - prior_context         (from golden_eval.jsonl)
  - retrieved_evidence    (from results/phase5/eval_predictions_main_agent.jsonl)
  - routing_decision      (auto_handle / escalate)
  - target customer message
  - predicted reply

Row ordering:
  - 30 clusters selected from results/phase6/human_ratings_90.jsonl (same sample)
  - Clusters shuffled deterministically (random.seed(42)) at cluster level
  - Within each cluster: Alpha/Beta/Gamma rows kept (system labels in hidden sheet 2)
  - Human rating columns (relevance, grounding, usefulness, tone, critical_error) are BLANK

Outputs (never overwrites v1 workbooks):
  results/phase6/reply_human_review_task_v2.xlsx
  results/phase6/human_ratings_90_v2.jsonl

DO NOT fill human review columns automatically.
Human annotators must complete them independently.
"""

import json
import random
from pathlib import Path
import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
PHASE5_DIR = ROOT / "results" / "phase5"
PHASE6_DIR = ROOT / "results" / "phase6"
GOLDEN_EVAL_PATH = ROOT / "golden_eval.jsonl"
OLD_RATINGS_PATH = PHASE6_DIR / "human_ratings_90.jsonl"
OUT_XLSX = PHASE6_DIR / "reply_human_review_task_v2.xlsx"
OUT_JSONL = PHASE6_DIR / "human_ratings_90_v2.jsonl"

SYSTEM_ORDER = ["baseline_0_majority", "baseline_1_rules", "main_agent_v1"]
SYSTEM_ALIAS_MAP = {
    "baseline_0_majority": "System_Alpha",
    "baseline_1_rules": "System_Beta",
    "main_agent_v1": "System_Gamma",
}
RANDOM_SEED = 42


def load_jsonl(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_gold_map():
    records = load_jsonl(GOLDEN_EVAL_PATH)
    return {r["example_id"]: r for r in records}


def load_predictions_by_system():
    """Returns dict: system_id → {example_id: pred}"""
    result = {}
    for sys_id, fname in [
        ("baseline_0_majority", "eval_predictions_baseline_0.jsonl"),
        ("baseline_1_rules", "eval_predictions_baseline_1.jsonl"),
        ("main_agent_v1", "eval_predictions_main_agent.jsonl"),
    ]:
        preds = load_jsonl(PHASE5_DIR / fname)
        result[sys_id] = {p["example_id"]: p for p in preds}
    return result


def build_retrieved_evidence_map(preds_by_system):
    """
    Build evidence string per example_id from main_agent retrieved_source_ids.
    """
    evidence_map = {}
    for eid, pred in preds_by_system["main_agent_v1"].items():
        src_ids = pred.get("retrieved_source_ids", [])
        if src_ids:
            evidence_map[eid] = "Retrieved from historical exchange: " + "; ".join(src_ids)
        else:
            evidence_map[eid] = "(No historical evidence retrieved)"
    return evidence_map


def get_sample_cluster_ids():
    """Read the 30 cluster example_ids from existing human_ratings_90.jsonl."""
    ratings = load_jsonl(OLD_RATINGS_PATH)
    seen = {}
    # maintain original cluster order from v1 file, deduplicate
    for r in ratings:
        eid = r["example_id"]
        if eid not in seen:
            seen[eid] = True
    cluster_ids = list(seen.keys())
    assert len(cluster_ids) == 30, f"Expected 30 clusters, got {len(cluster_ids)}"
    return cluster_ids


def build_rows(cluster_ids, gold_map, preds_by_system, evidence_map):
    """Build the 90 annotation rows with all required columns."""
    # Shuffle clusters deterministically
    rng = random.Random(RANDOM_SEED)
    shuffled_clusters = cluster_ids[:]
    rng.shuffle(shuffled_clusters)

    rows = []
    for row_cluster_idx, eid in enumerate(shuffled_clusters):
        gold = gold_map.get(eid, {})
        prior_context = gold.get("prior_context", "") or "(No prior context)"
        customer_message = gold.get("message", "(Unknown)")
        evidence = evidence_map.get(eid, "(No evidence retrieved)")

        # Shuffle system order within cluster (deterministic per cluster)
        cluster_rng = random.Random(RANDOM_SEED + row_cluster_idx)
        system_order_shuffled = SYSTEM_ORDER[:]
        cluster_rng.shuffle(system_order_shuffled)

        for rank, sys_id in enumerate(system_order_shuffled):
            pred = preds_by_system[sys_id].get(eid, {})
            predicted_reply = pred.get("predicted_reply", "(No reply available)")
            predicted_must_escalate = pred.get("predicted_must_escalate", None)
            routing_decision = (
                "ESCALATE to human agent" if predicted_must_escalate
                else "AUTO-HANDLE (bot reply)" if predicted_must_escalate is False
                else "(Unknown routing)"
            )

            rows.append({
                "row_id": f"R{row_cluster_idx + 1:02d}_{rank + 1}",
                "cluster_idx": row_cluster_idx + 1,
                "example_id": eid,
                "system_id": sys_id,                          # kept for jsonl, hidden in xlsx
                "system_alias": SYSTEM_ALIAS_MAP[sys_id],     # shown in xlsx
                "prior_context": prior_context,
                "customer_message": customer_message,
                "retrieved_evidence": evidence,
                "routing_decision": routing_decision,
                "predicted_reply": predicted_reply,
                # Human rating columns — BLANK
                "relevance_human": "",
                "grounding_human": "",
                "usefulness_human": "",
                "tone_human": "",
                "critical_error_human": "",
                "annotator_id": "",
                "notes": "",
                "status": "pending_human_review",
            })

    return rows


def save_jsonl(rows, path: Path):
    """Save annotation template as JSONL with human_scores dict."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            entry = {
                "example_id": r["example_id"],
                "system_id": r["system_id"],
                "system_alias": r["system_alias"],
                "row_id": r["row_id"],
                "prior_context": r["prior_context"],
                "customer_message": r["customer_message"],
                "retrieved_evidence": r["retrieved_evidence"],
                "routing_decision": r["routing_decision"],
                "predicted_reply": r["predicted_reply"],
                "human_scores": {
                    "relevance": None,
                    "grounding": None,
                    "usefulness": None,
                    "tone": None,
                    "critical_error": None,
                },
                "annotator_id": None,
                "notes": None,
                "status": "pending_human_review",
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[OK] Saved template JSONL -> {path}")


def save_xlsx(rows, path: Path):
    """Save annotator workbook with two sheets: main annotation + system key."""
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    # -------------------------------------------------------
    # Sheet 1: Instructions
    # -------------------------------------------------------
    ws_info = wb.active
    ws_info.title = "Instructions"

    header_fill = PatternFill("solid", fgColor="1DB954")  # Spotify green
    header_font = Font(bold=True, color="FFFFFF", size=13)
    ws_info.column_dimensions["A"].width = 100

    instructions = [
        ("REPLY-QUALITY HUMAN ANNOTATION WORKBOOK (v2)", True),
        ("", False),
        ("PURPOSE", True),
        ("You will rate 90 customer support replies across 5 quality dimensions.", False),
        ("Rows are grouped in clusters of 3: each cluster is one customer message", False),
        ("answered by 3 different systems (shown as System_Alpha, Beta, Gamma).", False),
        ("The system-to-alias mapping is in the 'System Key' sheet — review AFTER rating.", False),
        ("", False),
        ("COLUMNS PROVIDED FOR ASSESSMENT", True),
        ("  prior_context      — conversation turns before the target message (if any).", False),
        ("  customer_message   — the message the system must reply to.", False),
        ("  retrieved_evidence — historical evidence used to ground the reply.", False),
        ("  routing_decision   — whether the system chose to auto-reply or escalate.", False),
        ("  predicted_reply    — the system's draft reply (rate this).", False),
        ("", False),
        ("RATING SCALE (0–2)", True),
        ("  Relevance    0=Off-topic  1=Partial  2=Directly addresses inquiry", False),
        ("  Grounding    0=False claims  1=Generic/unverified  2=Grounded in Spotify policy", False),
        ("  Usefulness   0=No help  1=General steps  2=Direct link or clear resolution", False),
        ("  Tone         0=Rude  1=Dry/boilerplate  2=Warm, empathetic, professional", False),
        ("  Critical Error   0=No critical error  1=Critical error present", False),
        ("", False),
        ("CRITICAL ERROR = any of:", True),
        ("  1. Promises unverified financial refund or compensation.", False),
        ("  2. Confirms unverified global server outage.", False),
        ("  3. Claims manual backend account modification by bot.", False),
        ("  4. Auto-handles a case that should have been escalated to a human.", False),
        ("", False),
        ("INSTRUCTIONS", True),
        ("  1. Read prior_context, customer_message, and retrieved_evidence.", False),
        ("  2. Note the routing_decision (escalate vs auto_handle).", False),
        ("  3. Rate the predicted_reply on the 5 dimensions above.", False),
        ("  4. Enter your annotator_id in the annotator_id column.", False),
        ("  5. Do NOT look at the System Key sheet until you have finished all 90 rows.", False),
        ("", False),
        ("IMPORTANT — DO NOT:", True),
        ("  - Fill columns automatically or programmatically.", False),
        ("  - Leave any row partially filled — complete all 5 ratings per row.", False),
        ("  - Discuss ratings with others before completing your own.", False),
    ]

    for i, (text, is_header) in enumerate(instructions, start=1):
        cell = ws_info.cell(row=i, column=1, value=text)
        if is_header and text:
            cell.font = Font(bold=True, size=12)
            cell.fill = PatternFill("solid", fgColor="E8F5E9")

    # -------------------------------------------------------
    # Sheet 2: Main annotation sheet
    # -------------------------------------------------------
    ws = wb.create_sheet("Annotation")

    display_cols = [
        ("row_id", "Row ID", 10),
        ("system_alias", "System", 14),
        ("prior_context", "Prior Context", 45),
        ("customer_message", "Customer Message", 55),
        ("retrieved_evidence", "Retrieved Evidence", 45),
        ("routing_decision", "Routing Decision", 22),
        ("predicted_reply", "Predicted Reply", 60),
        # Rating columns
        ("relevance_human", "Relevance (0-2)", 14),
        ("grounding_human", "Grounding (0-2)", 14),
        ("usefulness_human", "Usefulness (0-2)", 15),
        ("tone_human", "Tone (0-2)", 12),
        ("critical_error_human", "Critical Error (0/1)", 18),
        ("annotator_id", "Annotator ID", 16),
        ("notes", "Notes", 30),
    ]

    # Header row
    for col_idx, (_, header, _) in enumerate(display_cols, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = PatternFill("solid", fgColor="1DB954")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Freeze header
    ws.freeze_panes = "A2"

    # Column widths
    for col_idx, (_, _, width) in enumerate(display_cols, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Alternate fill for clusters
    cluster_fill_a = PatternFill("solid", fgColor="F1F8E9")
    cluster_fill_b = PatternFill("solid", fgColor="FFFFFF")
    rating_fill = PatternFill("solid", fgColor="FFF9C4")  # Light yellow for rating cols
    rating_col_start = 8  # relevance_human onwards

    thin = Side(style="thin", color="CCCCCC")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    for row_idx, r in enumerate(rows, start=2):
        cluster_num = r["cluster_idx"]
        fill = cluster_fill_a if cluster_num % 2 == 1 else cluster_fill_b

        for col_idx, (key, _, _) in enumerate(display_cols, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=r.get(key, ""))
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border
            if col_idx >= rating_col_start:
                cell.fill = rating_fill
            else:
                cell.fill = fill

        # Row height
        ws.row_dimensions[row_idx].height = 80

    # -------------------------------------------------------
    # Sheet 3: System Key (hidden until after rating)
    # -------------------------------------------------------
    ws_key = wb.create_sheet("System Key (Open AFTER Rating)")
    ws_key.sheet_state = "hidden"  # Hidden by default

    ws_key.cell(row=1, column=1, value="SYSTEM IDENTITY KEY").font = Font(bold=True, size=12)
    ws_key.cell(row=2, column=1, value="Open this sheet only after completing all 90 ratings.")
    ws_key.cell(row=4, column=1, value="Alias").font = Font(bold=True)
    ws_key.cell(row=4, column=2, value="Actual System ID").font = Font(bold=True)
    for i, (sys_id, alias) in enumerate(SYSTEM_ALIAS_MAP.items(), start=5):
        ws_key.cell(row=i, column=1, value=alias)
        ws_key.cell(row=i, column=2, value=sys_id)
    ws_key.column_dimensions["A"].width = 18
    ws_key.column_dimensions["B"].width = 30

    wb.save(str(path))
    print(f"[OK] Saved annotation workbook -> {path}")


def main():
    print("=== Rebuilding Reply-Rating Workbook v2 ===")

    gold_map = load_gold_map()
    preds_by_system = load_predictions_by_system()
    evidence_map = build_retrieved_evidence_map(preds_by_system)
    cluster_ids = get_sample_cluster_ids()

    rows = build_rows(cluster_ids, gold_map, preds_by_system, evidence_map)

    assert len(rows) == 90, f"Expected 90 rows, got {len(rows)}"
    blank_check_cols = ["relevance_human", "grounding_human", "usefulness_human", "tone_human", "critical_error_human"]
    for col in blank_check_cols:
        assert all(r[col] == "" for r in rows), f"Column {col} must be blank in workbook"
    print(f"[OK] {len(rows)} rows built; all human rating columns verified blank.")

    # Check that prior_context column is populated vs. the v1 workbook
    has_context = sum(1 for r in rows if r["prior_context"] not in ("(No prior context)", ""))
    has_evidence = sum(1 for r in rows if "(No evidence" not in r["retrieved_evidence"])
    print(f"[OK] Rows with prior_context: {has_context}/90")
    print(f"[OK] Rows with retrieved_evidence: {has_evidence}/90")

    save_jsonl(rows, OUT_JSONL)
    save_xlsx(rows, OUT_XLSX)

    print("\n=== Done ===")
    print(f"  Workbook:  {OUT_XLSX}")
    print(f"  Template:  {OUT_JSONL}")
    print("\nIMPORTANT: Human rating columns (relevance, grounding, usefulness, tone, critical_error)")
    print("           are intentionally BLANK. Do NOT fill them programmatically.")
    print("           Ask a human annotator to complete them independently.")


if __name__ == "__main__":
    main()
