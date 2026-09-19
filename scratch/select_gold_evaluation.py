import json
import random
from pathlib import Path
from typing import Dict, Any, List

# Load eval_pool_inputs.jsonl
eval_path = Path("data/processed/v2/eval_pool_inputs.jsonl")
with open(eval_path, "r", encoding="utf-8") as f:
    eval_records = [json.loads(line) for line in f]

assert len(eval_records) == 1000

# Deterministic sorting before selection
eval_records.sort(key=lambda x: x["example_id"])

# 1. Challenge Candidate Scoring (Using INPUT-ONLY signals)
# Rules:
# - Security / Account Takeover signals (weight 4)
# - Multi-turn conversation depth > 1 (weight 3)
# - Competitor mentions / churn threats (weight 2)
# - Structural flags: multipart, url, partial_text, external_context, private_handoff (weight 1 each)

security_words = ['hack', 'stolen', 'compromis', 'unauthorized', 'someone else', 'logged into my', 'intruder']
competitor_words = ['apple music', 'tidal', 'pandora', 'deezer', 'amazon music', 'soundcloud', 'youtube music', 'switch to', 'leaving spotify']

challenge_candidates = []
for r in eval_records:
    score = 0
    text_lower = r["model_input_text"].lower()
    reasons = []
    
    # Check security
    if any(w in text_lower for w in security_words):
        score += 4
        reasons.append("security_threat")
        
    # Check multi-turn
    turns_cnt = len(r.get("ancestor_turns", []))
    if turns_cnt > 1:
        score += 3
        reasons.append(f"multi_turn_{turns_cnt}")
        
    # Check competitor / churn
    if any(w in text_lower for w in competitor_words):
        score += 2
        reasons.append("competitor_or_churn")
        
    # Check structural input flags
    flags = r.get("input_quality_flags", {})
    for flag_name, val in flags.items():
        if val:
            score += 1
            reasons.append(f"flag_{flag_name}")
            
    if score > 0:
        challenge_candidates.append((score, reasons, r))

# Sort candidates by score descending, then stable example_id
challenge_candidates.sort(key=lambda x: (-x[0], x[2]["example_id"]))

# Select top 50 challenge records
selected_challenge = []
selected_challenge_ids = set()

# To ensure diversity across challenge categories, pick balanced mix
for score, reasons, r in challenge_candidates:
    if len(selected_challenge) >= 50:
        break
    selected_challenge.append({
        "record": r,
        "challenge_score": score,
        "challenge_reasons": reasons
    })
    selected_challenge_ids.add(r["example_id"])

assert len(selected_challenge) == 50
print(f"Selected 50 challenge examples (scores range: {selected_challenge[0]['challenge_score']} to {selected_challenge[-1]['challenge_score']})")

# 2. Random Sampling (150 records from the remaining 950 records)
remaining_pool = [r for r in eval_records if r["example_id"] not in selected_challenge_ids]
assert len(remaining_pool) == 950

# Sort remaining stably by example_id before sampling
remaining_pool.sort(key=lambda x: x["example_id"])

rng = random.Random(42)
sampled_random = rng.sample(remaining_pool, 150)
selected_random_ids = {r["example_id"] for r in sampled_random}
assert len(selected_random_ids) == 150

# Check strictly disjoint
assert len(selected_challenge_ids & selected_random_ids) == 0

# 3. Create Gold Selection Manifest
manifest_entries = []

# Add challenge records
for item in selected_challenge:
    r = item["record"]
    entry = {
        "example_id": r["example_id"],
        "group_id": r["group_id"],
        "target_customer_tweet_id": r["target_customer_tweet_id"],
        "selected_brand_reply_tweet_id": r["selected_brand_reply_tweet_id"],
        "subset": "challenge",
        "challenge_reasons": item["challenge_reasons"],
        "challenge_score": item["challenge_score"],
        "model_input_text": r["model_input_text"],
        "ancestor_turns": r["ancestor_turns"],
        "input_quality_flags": r["input_quality_flags"],
        "created_at": r["created_at"],
    }
    manifest_entries.append(entry)

# Add random records
for r in sampled_random:
    entry = {
        "example_id": r["example_id"],
        "group_id": r["group_id"],
        "target_customer_tweet_id": r["target_customer_tweet_id"],
        "selected_brand_reply_tweet_id": r["selected_brand_reply_tweet_id"],
        "subset": "random",
        "challenge_reasons": [],
        "challenge_score": 0,
        "model_input_text": r["model_input_text"],
        "ancestor_turns": r["ancestor_turns"],
        "input_quality_flags": r["input_quality_flags"],
        "created_at": r["created_at"],
    }
    manifest_entries.append(entry)

# Sort manifest entries deterministically by subset then example_id
manifest_entries.sort(key=lambda x: (x["subset"], x["example_id"]))
assert len(manifest_entries) == 200

# Export manifest to destinations
manifest_destinations = [
    Path("data/manifests/v2/gold_selection_manifest.jsonl"),
    Path("results/phase2_v2/gold_selection_manifest.jsonl"),
    Path("gold_selection_manifest.jsonl"),
]

for dest in manifest_destinations:
    with open(dest, "w", encoding="utf-8") as f:
        for entry in manifest_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {len(manifest_entries)} gold selection records to {dest}")

print("Gold selection complete: 150 random + 50 challenge = 200 total (0 overlap).")
