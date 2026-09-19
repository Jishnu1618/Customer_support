"""
scratch/import_human_ratings.py
===============================
Imports the completed human ratings from reply_human_review_task_v2_annonated.xlsx
into human_ratings.csv and results/phase6/human_ratings_90.jsonl matching strictly on Review_ID.
"""

import json
from pathlib import Path
import pandas as pd

REPO_ROOT = Path("E:/Reply_agent")
EXCEL_PATH = REPO_ROOT / "reply_human_review_task_v2_annonated.xlsx"
CSV_PATH = REPO_ROOT / "human_ratings.csv"
JSONL_PATH = REPO_ROOT / "results" / "phase6" / "human_ratings_90.jsonl"
MAPPING_CSV = REPO_ROOT / "results" / "phase6" / "system_identity_mapping.csv"

def main():
    print(f"Reading annotated workbook: {EXCEL_PATH}...")
    df_excel = pd.read_excel(EXCEL_PATH)
    df_excel = df_excel.iloc[:90].copy()
    
    # Strip whitespace from review_id
    df_excel["Review_ID"] = df_excel["Review_ID"].astype(str).str.strip()
    
    print(f"Reading target human_ratings.csv: {CSV_PATH}...")
    df_csv = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)
    df_csv["review_id"] = df_csv["review_id"].astype(str).str.strip()
    
    excel_map = df_excel.set_index("Review_ID")
    
    updated_rows = 0
    for idx, row in df_csv.iterrows():
        rid = row["review_id"]
        if rid in excel_map.index:
            e_row = excel_map.loc[rid]
            
            # Extract scores as integers / clean strings
            rel = int(float(e_row["Human_Relevance"]))
            grd = int(float(e_row["Human_Grounding"]))
            use = int(float(e_row["Human_Usefulness"]))
            tone = int(float(e_row["Human_Tone"]))
            crit = int(float(e_row["Human_Critical_Error"]))
            annotator = str(e_row.get("Annotator_ID", "")).strip()
            notes = str(e_row.get("Notes", "")).strip()
            if notes.lower() == "nan":
                notes = ""
                
            df_csv.at[idx, "relevance_human"] = str(rel)
            df_csv.at[idx, "grounding_human"] = str(grd)
            df_csv.at[idx, "usefulness_human"] = str(use)
            df_csv.at[idx, "tone_human"] = str(tone)
            df_csv.at[idx, "critical_error_human"] = str(crit)
            df_csv.at[idx, "annotator_id"] = annotator
            df_csv.at[idx, "notes"] = notes
            updated_rows += 1
            
    print(f"Successfully matched and populated {updated_rows}/90 rows.")
    assert updated_rows == 90, f"Expected 90 updated rows, got {updated_rows}"
    
    # Save back to human_ratings.csv
    df_csv.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print(f"Saved populated ratings to {CSV_PATH}")
    
    # Also update JSONL
    records = df_csv.to_dict(orient="records")
    for r in records:
        r["relevance_human"] = int(r["relevance_human"])
        r["grounding_human"] = int(r["grounding_human"])
        r["usefulness_human"] = int(r["usefulness_human"])
        r["tone_human"] = int(r["tone_human"])
        r["critical_error_human"] = int(r["critical_error_human"])
        r["status"] = "completed_human_review"
        
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Saved populated ratings to {JSONL_PATH}")

if __name__ == "__main__":
    main()
