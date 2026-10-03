"""
eval_intent_model.py
Evaluates the fine-tuned DeBERTa model against the 200-sample gold benchmark (golden_eval.jsonl).
Measures:
  1. Overall Accuracy (vs 51.5% baseline)
  2. Macro F1 score
  3. Per-intent Precision, Recall, and F1
  4. Average CPU inference latency per query (in milliseconds)
"""
import os
import sys
import time
import json

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import torch
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, f1_score
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_DIR = "E:/Reply_agent/models/deberta-intent-spotify-best"
TEST_FILE = "golden_eval.jsonl"

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
ID_TO_LABEL = {v: k for k, v in INTENT_MAP.items()}

def main():
    if not os.path.exists(MODEL_DIR):
        print(f"[ERROR] Fine-tuned model directory not found: {MODEL_DIR}")
        print("Please run `python train_intent.py` first.")
        return

    print(f"--> Loading model from {MODEL_DIR}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()

    print(f"--> Loading benchmark from {TEST_FILE}...")
    gold_records = []
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                gold_records.append(json.loads(line))

    texts = []
    gold_labels = []
    for r in gold_records:
        intent = r.get("intent")
        text = r.get("message") or r.get("customer_message") or r.get("text", "")
        if intent in INTENT_MAP and text:
            texts.append(text)
            gold_labels.append(INTENT_MAP[intent])

    print(f"--> Evaluating {len(texts)} gold test cases with batched inference...")
    predictions = []
    batch_size = 32
    total_start = time.perf_counter()

    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            inputs = tokenizer(batch_texts, return_tensors="pt", truncation=True, max_length=128, padding=True)
            outputs = model(**inputs)
            preds = torch.argmax(outputs.logits, dim=-1).cpu().numpy().tolist()
            predictions.extend(preds)

    total_time = time.perf_counter() - total_start
    avg_latency = (total_time / len(texts)) * 1000.0

    acc = accuracy_score(gold_labels, predictions)
    macro_f1 = f1_score(gold_labels, predictions, average="macro", zero_division=0)

    print("\n" + "=" * 65)
    print("DEBERTA INTENT CLASSIFICATION EVALUATION ON GOLD BENCHMARK")
    print("=" * 65)
    print(f"Baseline Accuracy:        51.50%")
    print(f"Fine-Tuned Accuracy:      {acc * 100:.2f}%")
    print(f"Macro F1 Score:           {macro_f1:.4f}")
    print(f"Mean Latency per query:   {avg_latency:.2f} ms")
    print(f"Total Evaluation Time:    {total_time:.2f} s")
    print("=" * 65)
    print("\nDetailed Per-Class Breakdown:")
    target_names = [ID_TO_LABEL[i] for i in range(len(INTENT_MAP))]
    print(classification_report(gold_labels, predictions, target_names=target_names, digits=4, zero_division=0))

if __name__ == "__main__":
    main()
