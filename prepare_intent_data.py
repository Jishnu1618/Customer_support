"""
prepare_intent_data.py
Extracts and formats training and validation sets for DeBERTa intent classification.
Reads gold annotations from dev_gold.jsonl and golden_eval.jsonl.
Outputs:
  - data/intent_train.jsonl
  - data/intent_val.jsonl
"""
import os
import json
import pandas as pd
from sklearn.model_selection import train_test_split

INTENT_MAP = {
    "content_availability": 0,
    "technical_support": 1,
    "account_access": 2,
    "billing_and_payments": 3,
    "subscription_and_plans": 4,
    "platform_and_regional": 5,
    "product_feedback": 6,
    "other_or_ambiguous": 7
}

def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def main():
    os.makedirs("data", exist_ok=True)
    
    # 1. Load curated labeled data
    dev_records = load_jsonl("dev_gold.jsonl")
    gold_records = load_jsonl("golden_eval.jsonl")
    all_records = dev_records + gold_records
    
    rows = []
    for r in all_records:
        intent = r.get("intent")
        text = r.get("message") or r.get("customer_message") or r.get("text")
        if intent in INTENT_MAP and text:
            rows.append({
                "example_id": r.get("example_id", ""),
                "text": text.strip(),
                "intent": intent,
                "label": INTENT_MAP[intent]
            })
            
    df = pd.DataFrame(rows)
    print(f"Total labeled samples loaded: {len(df)}")
    print("\nClass distribution:")
    print(df["intent"].value_counts())
    
    # 2. Stratified train/validation split (80/20)
    train_df, val_df = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
        stratify=df["label"]
    )
    
    train_path = "data/intent_train.jsonl"
    val_path = "data/intent_val.jsonl"
    
    train_df.to_json(train_path, orient="records", lines=True, force_ascii=False)
    val_df.to_json(val_path, orient="records", lines=True, force_ascii=False)
    
    print(f"\n[OK] Successfully saved:")
    print(f"  - Train: {train_path} ({len(train_df)} samples)")
    print(f"  - Val:   {val_path} ({len(val_df)} samples)")

if __name__ == "__main__":
    main()
