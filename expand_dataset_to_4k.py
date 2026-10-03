"""
expand_dataset_to_4k.py
Extracts 4,000 clean, balanced training and validation samples across the 8 Spotify intents
by scanning twcs.csv and spotify_knowledge.jsonl, applying strict quality filters, and deduplicating.
Packages colab_bundle.zip for Google Colab training.
"""
import os
import re
import json
import zipfile
import pandas as pd
from sklearn.model_selection import train_test_split
from src.baselines import Baseline1RuleAgent

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

TARGET_PER_CLASS = 500  # 8 * 500 = 4,000 balanced samples

def clean_text(text):
    if not isinstance(text, str):
        return ""
    t = text.strip()
    # Filter out empty or too short/too long messages
    words = t.split()
    if len(words) < 4 or len(words) > 70:
        return ""
    # Filter out pure link or pure mention tweets
    non_mention_words = [w for w in words if not w.startswith("@") and not w.startswith("http")]
    if len(non_mention_words) < 3:
        return ""
    # Filter out trivial conversational non-issues
    low = t.lower()
    if re.search(r"^(thanks|thank you|ok thanks|dm sent|sent dm|done|check dm|pls reply|hello)\b", low):
        return ""
    return t

def main():
    print("--> Expanding dataset to 4,000 clean, balanced samples...")
    b1 = Baseline1RuleAgent()
    samples_by_intent = {k: [] for k in INTENT_MAP}
    seen_texts = set()

    # 1. Add curated dev samples first (highest quality)
    if os.path.exists("dev_gold.jsonl"):
        with open("dev_gold.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                intent = r.get("intent")
                text = r.get("message") or r.get("customer_message")
                c_text = clean_text(text)
                if intent in INTENT_MAP and c_text and c_text.lower() not in seen_texts:
                    seen_texts.add(c_text.lower())
                    samples_by_intent[intent].append({
                        "example_id": r.get("example_id", ""),
                        "text": c_text,
                        "intent": intent,
                        "label": INTENT_MAP[intent],
                        "source": "curated_dev"
                    })

    print(f"Loaded curated dev samples: {sum(len(v) for v in samples_by_intent.values())}")

    # 2. Add from spotify_knowledge.jsonl
    if os.path.exists("data/processed/spotify_knowledge.jsonl"):
        with open("data/processed/spotify_knowledge.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                text = clean_text(r.get("customer_text", ""))
                if not text or text.lower() in seen_texts:
                    continue
                pred = b1.predict({"message": text, "prior_context": ""})
                intent = pred["predicted_intent"]
                if intent in INTENT_MAP and len(samples_by_intent[intent]) < TARGET_PER_CLASS:
                    seen_texts.add(text.lower())
                    samples_by_intent[intent].append({
                        "example_id": r.get("example_id", ""),
                        "text": text,
                        "intent": intent,
                        "label": INTENT_MAP[intent],
                        "source": "spotify_knowledge"
                    })

    # 3. Scan twcs.csv for remaining needed samples across all classes
    needed = sum(max(0, TARGET_PER_CLASS - len(v)) for v in samples_by_intent.values())
    print(f"Samples needed from twcs.csv to reach 4,000: {needed}")

    if needed > 0 and os.path.exists("twcs.csv"):
        print("Scanning twcs.csv for Spotify inquiries...")
        for chunk in pd.read_csv("twcs.csv", chunksize=100000, usecols=["author_id", "text", "inbound"]):
            # Get tweets addressed to Spotify or inbound customer tweets
            inbound_tweets = chunk[chunk["inbound"] == True]
            for _, row in inbound_tweets.iterrows():
                raw_text = str(row["text"])
                if "@SpotifyCares" not in raw_text and "@Spotify" not in raw_text:
                    continue
                text = clean_text(raw_text)
                if not text or text.lower() in seen_texts:
                    continue
                pred = b1.predict({"message": text, "prior_context": ""})
                intent = pred["predicted_intent"]
                if intent in INTENT_MAP and len(samples_by_intent[intent]) < TARGET_PER_CLASS:
                    seen_texts.add(text.lower())
                    samples_by_intent[intent].append({
                        "example_id": f"twcs_{len(seen_texts)}",
                        "text": text,
                        "intent": intent,
                        "label": INTENT_MAP[intent],
                        "source": "twcs_silver"
                    })
            # Check if all classes reached target
            if all(len(samples_by_intent[k]) >= TARGET_PER_CLASS for k in INTENT_MAP):
                print("All classes reached 500 samples target!")
                break

    all_rows = []
    for intent, items in samples_by_intent.items():
        all_rows.extend(items)

    df = pd.DataFrame(all_rows)
    print("\n" + "=" * 50)
    print(f"FINAL 4,000 DATASET DISTRIBUTION (Total: {len(df)}):")
    print(df["intent"].value_counts())
    print("=" * 50)

    # 4. Stratified Train / Val split (85% Train, 15% Val)
    train_df, val_df = train_test_split(
        df,
        test_size=0.15,
        random_state=42,
        stratify=df["label"]
    )

    os.makedirs("data", exist_ok=True)
    train_path = "data/colab_intent_train_4k.jsonl"
    val_path = "data/colab_intent_val_4k.jsonl"

    train_df.to_json(train_path, orient="records", lines=True, force_ascii=False)
    val_df.to_json(val_path, orient="records", lines=True, force_ascii=False)
    print(f"\n[OK] Saved Train ({len(train_df)}) -> {train_path}")
    print(f"[OK] Saved Val   ({len(val_df)}) -> {val_path}")

    # 5. Pack into colab_bundle.zip (with untouched golden_eval.jsonl)
    zip_path = "colab_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(train_path, arcname="intent_train.jsonl")
        zf.write(val_path, arcname="intent_val.jsonl")
        zf.write("golden_eval.jsonl", arcname="golden_eval.jsonl")

    size_kb = os.path.getsize(zip_path) / 1024
    print(f"[OK] Successfully updated {zip_path} ({size_kb:.1f} KB)")
    print("Ready to run on Google Colab!")

if __name__ == "__main__":
    main()
