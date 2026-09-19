import sys
import json
from pathlib import Path

REPO_ROOT = Path("E:/Reply_agent")
sys.path.insert(0, str(REPO_ROOT))

from src.prepare_phase2_dataset import (
    get_db_connection,
    DB_PATH,
    load_review_exclusion_root_ids,
    extract_phase2_candidates,
    export_phase2_outputs,
    create_partitions,
    deduplicate_and_audit_leakage,
    OUTPUT_REPORT_DIR,
    RANDOM_SEED,
    TARGET_HISTORICAL,
    TARGET_DEV,
    TARGET_EVAL_POOL,
)
from src.language_filter import export_human_review_sheet

def main():
    conn = get_db_connection(DB_PATH)
    cursor = conn.cursor()
    review_excluded_roots = load_review_exclusion_root_ids()
    candidates, raw_exclusions, uncertain_cases, non_english_cases = extract_phase2_candidates(
        cursor, review_excluded_roots, return_non_english=True
    )
    conn.close()

    print(f"Total valid candidates: {len(candidates)}")
    print(f"Total non-English cases: {len(non_english_cases)}")
    print(f"Total uncertain cases: {len(uncertain_cases)}")

    # Test writing the review queue
    queue_path = OUTPUT_REPORT_DIR / "language_review_queue.json"
    queue_payload = {
        "status": "pending_human_review",
        "policy": "Uncertain language cases are placed in this review queue and excluded from English-only splits pending human verification.",
        "total_uncertain_cases": len(uncertain_cases),
        "cases": uncertain_cases,
    }
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue_payload, f, indent=2, ensure_ascii=False)
    print(f"Successfully wrote language_review_queue.json ({len(uncertain_cases)} cases)")

    # Test writing the human review sheet: 10 accepted, 10 rejected, 10 uncertain
    accepted_sample = [{**item, "sample_category": "accepted"} for item in candidates[:10]]
    rejected_sample = non_english_cases[:10]
    uncertain_sample = uncertain_cases[:10]
    sample_records = accepted_sample + rejected_sample + uncertain_sample

    sheet_path = OUTPUT_REPORT_DIR / "language_human_review_sheet.csv"
    export_human_review_sheet(sample_records, sheet_path)
    print(f"Successfully wrote language_human_review_sheet.csv ({len(sample_records)} cases)")

    # Verify review sheet columns
    import csv
    with open(sheet_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        print(f"Review sheet has {len(reader)} rows and columns: {list(reader[0].keys())}")
        for r in reader:
            assert r["human_language_label"] == ""
            assert r["human_interpretability_label"] == ""
            assert r["human_notes"] == ""
    print("All human label columns verified blank!")

if __name__ == "__main__":
    main()
