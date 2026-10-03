"""
train_intent.py
Fine-tunes microsoft/deberta-v3-small for 8-class Spotify customer support intent classification.
All cache and model checkpoints are saved to D:/hf_cache and E:/Reply_agent/models to protect C: drive space.
"""
import os
import sys

# Ensure Hugging Face cache uses D: drive to protect C: drive space
os.environ["HF_HOME"] = os.getenv("HF_HOME", "D:/hf_cache")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import torch
import numpy as np
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
from sklearn.metrics import accuracy_score, f1_score

MODEL_ID = "microsoft/deberta-v3-small"
CACHE_DIR = os.environ["HF_HOME"]
OUTPUT_DIR = "E:/Reply_agent/models/deberta-intent-spotify"
BEST_MODEL_DIR = "E:/Reply_agent/models/deberta-intent-spotify-best"

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
    print(f"--> Using Hugging Face Cache: {CACHE_DIR}")
    print(f"--> PyTorch device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    
    # 1. Load tokenizer & dataset
    print(f"--> Loading tokenizer for {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=CACHE_DIR)
    
    data_files = {
        "train": "data/intent_train.jsonl",
        "validation": "data/intent_val.jsonl"
    }
    dataset = load_dataset("json", data_files=data_files)
    print(f"--> Loaded {len(dataset['train'])} train and {len(dataset['validation'])} val samples.")
    
    def tokenize_fn(batch):
        return tokenizer(batch["text"], truncation=True, max_length=128)
    
    print("--> Tokenizing dataset...")
    tokenized_dataset = dataset.map(tokenize_fn, batched=True)
    
    # 2. Metrics (using scikit-learn)
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        acc = accuracy_score(labels, preds)
        macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
        return {"accuracy": acc, "macro_f1": macro_f1}
    
    # 3. Load base model
    print(f"--> Initializing {MODEL_ID} (8 output labels)...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        num_labels=len(INTENT_MAP),
        id2label=ID_TO_LABEL,
        label2id=INTENT_MAP,
        cache_dir=CACHE_DIR
    )
    
    # 4. Training configuration
    use_cuda = torch.cuda.is_available()
    batch_size = 16 if use_cuda else 8
    epochs = 4 if use_cuda else 3
    
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        learning_rate=2e-5,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        num_train_epochs=epochs,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        fp16=use_cuda,
        logging_steps=10,
        report_to="none"
    )
    
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )
    
    print("--> Starting fine-tuning...")
    trainer.train()
    
    print(f"\n--> Saving best model to {BEST_MODEL_DIR}...")
    os.makedirs(BEST_MODEL_DIR, exist_ok=True)
    trainer.save_model(BEST_MODEL_DIR)
    tokenizer.save_pretrained(BEST_MODEL_DIR)
    
    print("--> Evaluating best model on validation split...")
    eval_results = trainer.evaluate()
    print("\n" + "=" * 50)
    print("FINAL VALIDATION EVALUATION RESULTS:")
    for k, v in eval_results.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    print("=" * 50)
    print(f"\n[SUCCESS] DeBERTa fine-tuning complete! Model saved to {BEST_MODEL_DIR}")

if __name__ == "__main__":
    main()
