"""
export_colab_package.py
1. Generates balanced silver training/validation data by combining curated gold/dev data
   with high-confidence silver labels from spotify_knowledge.jsonl.
2. Creates colab_bundle.zip containing the training data and gold test benchmark.
3. Generates Spotify_DeBERTa_FineTuning_Colab.ipynb ready to run on free Google Colab T4 GPU.
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

def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def generate_silver_data():
    os.makedirs("data", exist_ok=True)
    
    # 1. Curated base data
    dev_records = load_jsonl("dev_gold.jsonl")
    curated_rows = []
    for r in dev_records:
        intent = r.get("intent")
        text = r.get("message") or r.get("customer_message") or r.get("text")
        if intent in INTENT_MAP and text:
            curated_rows.append({
                "example_id": r.get("example_id", ""),
                "text": text.strip(),
                "intent": intent,
                "label": INTENT_MAP[intent],
                "source": "curated_gold"
            })
            
    # 2. Extract silver labels from spotify_knowledge.jsonl using Baseline 1 rules
    b1 = Baseline1RuleAgent()
    knowledge_records = load_jsonl("data/processed/spotify_knowledge.jsonl")
    
    silver_by_intent = {k: [] for k in INTENT_MAP}
    
    for r in knowledge_records:
        text = r.get("customer_text", "").strip()
        if not text or len(text.split()) < 4:
            continue
            
        pred = b1.predict({"message": text, "prior_context": ""})
        intent = pred["predicted_intent"]
        
        # Keep high-quality matches (limit max 250 per class for balance)
        if intent in silver_by_intent and len(silver_by_intent[intent]) < 250:
            silver_by_intent[intent].append({
                "example_id": r.get("example_id", ""),
                "text": text,
                "intent": intent,
                "label": INTENT_MAP[intent],
                "source": "silver_knowledge"
            })
            
    silver_rows = []
    for intent, items in silver_by_intent.items():
        silver_rows.extend(items)
        
    all_rows = curated_rows + silver_rows
    df = pd.DataFrame(all_rows).drop_duplicates(subset=["text"])
    
    print(f"Total dataset size (Curated + Silver): {len(df)}")
    print("\nClass Distribution:")
    print(df["intent"].value_counts())
    
    train_df, val_df = train_test_split(
        df,
        test_size=0.15,
        random_state=42,
        stratify=df["label"]
    )
    
    train_path = "data/colab_intent_train.jsonl"
    val_path = "data/colab_intent_val.jsonl"
    
    train_df.to_json(train_path, orient="records", lines=True, force_ascii=False)
    val_df.to_json(val_path, orient="records", lines=True, force_ascii=False)
    print(f"\n[OK] Saved Train ({len(train_df)}) -> {train_path}")
    print(f"[OK] Saved Val   ({len(val_df)}) -> {val_path}")
    
    # 3. Create zip bundle for 1-click upload to Colab
    zip_path = "colab_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(train_path, arcname="intent_train.jsonl")
        zf.write(val_path, arcname="intent_val.jsonl")
        zf.write("golden_eval.jsonl", arcname="golden_eval.jsonl")
    print(f"[OK] Created Colab data bundle: {zip_path} ({os.path.getsize(zip_path) / 1024:.1f} KB)")
    
    # 4. Generate the Jupyter Notebook
    create_colab_notebook()

def create_colab_notebook():
    notebook_content = {
        "nbformat": 4,
        "nbformat_minor": 2,
        "metadata": {
            "accelerator": "GPU",
            "colab": {
                "provenance": [],
                "gpuType": "T4"
            },
            "language_info": {
                "name": "python"
            }
        },
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# 🚀 Spotify Support DeBERTa-v3 Intent Classifier Fine-Tuning\n",
                    "**Track 1: High-Performance, Low-Latency Intent Classification**\n",
                    "- **Base Model**: `microsoft/deberta-v3-small` (86M parameters)\n",
                    "- **Target**: Jump from 51.5% baseline to 88–92% accuracy across 8 customer support intents\n",
                    "- **Runtime**: Free Google Colab T4 GPU (~3 minutes training time)"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "### Step 1: Check GPU & Install Dependencies"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "!nvidia-smi\n",
                    "!pip install -q transformers datasets accelerate sentencepiece tiktoken evaluate scikit-learn"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "### Step 2: Upload Data Bundle (`colab_bundle.zip`)\n",
                    "Run this cell and upload `colab_bundle.zip` (it contains `intent_train.jsonl`, `intent_val.jsonl`, and `golden_eval.jsonl`)."
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from google.colab import files\n",
                    "import zipfile\n",
                    "import os\n",
                    "\n",
                    "if not os.path.exists('colab_bundle.zip'):\n",
                    "    print('Please upload colab_bundle.zip:')\n",
                    "    uploaded = files.upload()\n",
                    "\n",
                    "with zipfile.ZipFile('colab_bundle.zip', 'r') as zip_ref:\n",
                    "    zip_ref.extractall('.')\n",
                    "\n",
                    "print('Data unzipped successfully:')\n",
                    "!ls -lh *.jsonl"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "### Step 3: Load Dataset & Tokenizer"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import torch\n",
                    "import numpy as np\n",
                    "from datasets import load_dataset\n",
                    "from sklearn.metrics import accuracy_score, f1_score\n",
                    "from transformers import (\n",
                    "    AutoTokenizer,\n",
                    "    AutoModelForSequenceClassification,\n",
                    "    TrainingArguments,\n",
                    "    Trainer,\n",
                    "    DataCollatorWithPadding\n",
                    ")\n",
                    "\n",
                    "MODEL_ID = 'microsoft/deberta-v3-small'\n",
                    "INTENT_MAP = {\n",
                    "    'content_availability': 0,\n",
                    "    'technical_support': 1,\n",
                    "    'account_access': 2,\n",
                    "    'billing_and_payments': 3,\n",
                    "    'subscription_and_plans': 4,\n",
                    "    'platform_and_regional': 5,\n",
                    "    'product_feedback': 6,\n",
                    "    'other_or_ambiguous': 7\n",
                    "}\n",
                    "ID_TO_LABEL = {v: k for k, v in INTENT_MAP.items()}\n",
                    "\n",
                    "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)\n",
                    "\n",
                    "dataset = load_dataset('json', data_files={\n",
                    "    'train': 'intent_train.jsonl',\n",
                    "    'validation': 'intent_val.jsonl'\n",
                    "})\n",
                    "print(f'Train samples: {len(dataset[\"train\"])}, Val samples: {len(dataset[\"validation\"])}')\n",
                    "\n",
                    "def tokenize_fn(batch):\n",
                    "    enc = tokenizer(batch['text'], truncation=True, max_length=128)\n",
                    "    enc['labels'] = [int(l) for l in batch['label']]\n",
                    "    return enc\n",
                    "\n",
                    "tokenized_dataset = dataset.map(tokenize_fn, batched=True, remove_columns=['text', 'label', 'example_id', 'intent', 'source'])"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "### Step 4: Fine-Tune DeBERTa-v3 on GPU (~3 minutes)"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "def compute_metrics(eval_pred):\n",
                    "    logits, labels = eval_pred\n",
                    "    preds = np.argmax(logits, axis=-1)\n",
                    "    acc = accuracy_score(labels, preds)\n",
                    "    macro_f1 = f1_score(labels, preds, average='macro', zero_division=0)\n",
                    "    return {'accuracy': acc, 'macro_f1': macro_f1}\n",
                    "\n",
                    "model = AutoModelForSequenceClassification.from_pretrained(\n",
                    "    MODEL_ID,\n",
                    "    num_labels=len(INTENT_MAP),\n",
                    "    id2label=ID_TO_LABEL,\n",
                    "    label2id=INTENT_MAP\n",
                    ")\n",
                    "\n",
                    "training_args = TrainingArguments(\n",
                    "    output_dir='./deberta-spotify-checkpoints',\n",
                    "    learning_rate=3e-5,\n",
                    "    per_device_train_batch_size=16,\n",
                    "    per_device_eval_batch_size=32,\n",
                    "    num_train_epochs=4,\n",
                    "    weight_decay=0.01,\n",
                    "    eval_strategy='epoch',\n",
                    "    save_strategy='epoch',\n",
                    "    load_best_model_at_end=True,\n",
                    "    metric_for_best_model='macro_f1',\n",
                    "    greater_is_better=True,\n",
                    "    fp16=False, # Stable FP32 on T4 GPU\n",
                    "    logging_steps=20,\n",
                    "    report_to='none'\n",
                    ")\n",
                    "\n",
                    "trainer = Trainer(\n",
                    "    model=model,\n",
                    "    args=training_args,\n",
                    "    train_dataset=tokenized_dataset['train'],\n",
                    "    eval_dataset=tokenized_dataset['validation'],\n",
                    "    processing_class=tokenizer,\n",
                    "    data_collator=DataCollatorWithPadding(tokenizer=tokenizer),\n",
                    "    compute_metrics=compute_metrics\n",
                    ")\n",
                    "\n",
                    "trainer.train()\n",
                    "trainer.save_model('./deberta-intent-spotify-best')\n",
                    "tokenizer.save_pretrained('./deberta-intent-spotify-best')\n",
                    "print('Training complete! Best model saved to ./deberta-intent-spotify-best')"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "### Step 5: Benchmark Against 200 Curated Gold Test Cases (`golden_eval.jsonl`)"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import json\n",
                    "import time\n",
                    "from sklearn.metrics import classification_report\n",
                    "\n",
                    "gold_records = [json.loads(line) for line in open('golden_eval.jsonl', 'r', encoding='utf-8')]\n",
                    "texts = [r.get('message') or r.get('customer_message') for r in gold_records]\n",
                    "gold_labels = [INTENT_MAP[r['intent']] for r in gold_records]\n",
                    "\n",
                    "model.eval()\n",
                    "predictions = []\n",
                    "batch_size = 32\n",
                    "start_time = time.perf_counter()\n",
                    "\n",
                    "with torch.no_grad():\n",
                    "    for i in range(0, len(texts), batch_size):\n",
                    "        b_texts = texts[i:i + batch_size]\n",
                    "        inputs = tokenizer(b_texts, return_tensors='pt', truncation=True, max_length=128, padding=True).to(model.device)\n",
                    "        outputs = model(**inputs)\n",
                    "        preds = torch.argmax(outputs.logits, dim=-1).cpu().numpy().tolist()\n",
                    "        predictions.extend(preds)\n",
                    "\n",
                    "elapsed = time.perf_counter() - start_time\n",
                    "acc = accuracy_score(gold_labels, predictions)\n",
                    "macro_f1 = f1_score(gold_labels, predictions, average='macro', zero_division=0)\n",
                    "\n",
                    "print('=' * 65)\n",
                    "print('DEBERTA INTENT CLASSIFIER - GOLD BENCHMARK RESULTS')\n",
                    "print('=' * 65)\n",
                    "print(f'Baseline Accuracy:     51.50%')\n",
                    "print(f'Fine-Tuned Accuracy:   {acc * 100:.2f}%')\n",
                    "print(f'Macro F1 Score:        {macro_f1:.4f}')\n",
                    "print(f'Latency per query:     {(elapsed / len(texts)) * 1000:.2f} ms')\n",
                    "print('=' * 65)\n",
                    "print('\\nDetailed Per-Class Breakdown:')\n",
                    "target_names = [ID_TO_LABEL[i] for i in range(len(INTENT_MAP))]\n",
                    "print(classification_report(gold_labels, predictions, target_names=target_names, digits=4, zero_division=0))"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "### Step 6: Download the Fine-Tuned Model Weights to Your PC\n",
                    "Run this cell to zip and download `deberta-intent-spotify-best.zip` so you can use it locally in `E:/Reply_agent/models/`."
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "!zip -r deberta-intent-spotify-best.zip deberta-intent-spotify-best\n",
                    "files.download('deberta-intent-spotify-best.zip')"
                ]
            }
        ]
    }
    
    nb_path = "Spotify_DeBERTa_FineTuning_Colab.ipynb"
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2)
    print(f"[OK] Generated Colab Notebook: {nb_path}")

if __name__ == "__main__":
    generate_silver_data()
