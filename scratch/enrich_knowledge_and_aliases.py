import json
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple

db_path = Path("data/cache/twcs_index.sqlite")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

knowledge_path = Path("data/processed/v2/spotify_knowledge.jsonl")
with open(knowledge_path, "r", encoding="utf-8") as f:
    items = [json.loads(line) for line in f]

assert len(items) == 3000

confirmed_tokens = ["thank", "thx", "fixed", "works now", "working now", "it worked", "got it", "solved", "perfect", "awesome", "great", "helped", "all good", "appreciate it"]
unclear_tokens = ["still", "not working", "didn't work", "did not work", "doesn't work", "does not work", "same error", "already tried", "sent a dm", "dm sent", "sent dm", "messaged you", "nothing"]

outcome_counts = {"confirmed": 0, "unconfirmed": 0, "unclear": 0}
enriched_items = []

for item in items:
    reply_id = item["selected_brand_reply_tweet_id"]
    reply_text = item["brand_reply_text"].lower()
    
    cursor.execute("SELECT tweet_id, author_id, text, inbound FROM tweets WHERE in_response_to_tweet_id = ?", (reply_id,))
    followup_tweets = cursor.fetchall()
    
    if not followup_tweets:
        if any(w in reply_text for w in ["dm us", "send us a dm", "private message", "reach out via dm", "dm me"]):
            outcome = "unclear"
            reason = "unresolved_private_handoff_requested"
        else:
            outcome = "unconfirmed"
            reason = "support_action_delivered_no_customer_followup"
    else:
        cust_followups = [t for t in followup_tweets if t["inbound"] == 1]
        if not cust_followups:
            outcome = "unconfirmed"
            reason = "internal_brand_followup_only"
        else:
            followup_text = " ".join([t["text"].lower() for t in cust_followups])
            if any(w in followup_text for w in confirmed_tokens):
                outcome = "confirmed"
                reason = "customer_confirmed_resolution"
            elif any(w in followup_text for w in unclear_tokens):
                outcome = "unclear"
                reason = "customer_reported_persisting_issue"
            elif any(w in reply_text for w in ["dm us", "send us a dm", "private message"]):
                outcome = "unclear"
                reason = "private_handoff_in_progress"
            else:
                outcome = "unconfirmed"
                reason = "customer_responded_without_explicit_resolution"
                
    outcome_counts[outcome] += 1
    
    item_copy = dict(item)
    item_copy["outcome"] = outcome
    item_copy["outcome_reason"] = reason
    enriched_items.append(item_copy)

print(f"Outcome distribution across 3,000 historical knowledge records:")
for k, v in outcome_counts.items():
    print(f"  - {k}: {v} ({v/3000*100:.1f}%)")

# Write back to spotify_knowledge.jsonl
with open(knowledge_path, "w", encoding="utf-8") as f:
    for rec in enriched_items:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"Updated {knowledge_path}")

# Create canonical aliases
alias_knowledge = Path("data/processed/v2/knowledge.jsonl")
shutil.copyfile(knowledge_path, alias_knowledge)
print(f"Created alias: {alias_knowledge}")

eval_pool_src = Path("data/processed/v2/eval_pool_inputs.jsonl")
alias_eval_pool = Path("data/processed/v2/eval_pool.jsonl")
shutil.copyfile(eval_pool_src, alias_eval_pool)
print(f"Created alias: {alias_eval_pool}")

exclusions_src = Path("results/phase2_v2/exclusion_summary.json")
alias_exclusions = Path("results/phase2_v2/exclusions.json")
shutil.copyfile(exclusions_src, alias_exclusions)
print(f"Created alias: {alias_exclusions}")

# Update data_summary.md with retrospective sampling label and outcome counts
summary_path = Path("results/phase2_v2/data_summary.md")
summary_content = summary_path.read_text(encoding="utf-8")

retrospective_section = f"""
## Sampling Strategy & Experiment Label
- **Experiment Type**: **Retrospective Sampling** (not strictly chronological).
- **Sampling Mechanism**: Seed 42 deterministic shuffle over all 27,000+ eligible conversation groups from the 2017 Twitter Customer Support Corpus.
- **Historical Support Outcomes Distribution (3,000 Groups)**:
  - `unconfirmed`: {outcome_counts['unconfirmed']} ({outcome_counts['unconfirmed']/3000*100:.1f}%) — Standard support action delivered with no further customer reply.
  - `unclear`: {outcome_counts['unclear']} ({outcome_counts['unclear']/3000*100:.1f}%) — Inquiries ending in unresolved private handoff ("DM us") or continuing back-and-forth.
  - `confirmed`: {outcome_counts['confirmed']} ({outcome_counts['confirmed']/3000*100:.1f}%) — Customer explicitly confirmed resolution ("thanks", "fixed", "worked").
"""

if "## Sampling Strategy & Experiment Label" not in summary_content:
    summary_content = summary_content.replace(
        "## Partition Sizes & Shortfalls (Measured On Disk)",
        retrospective_section + "\n## Partition Sizes & Shortfalls (Measured On Disk)"
    )
    summary_path.write_text(summary_content, encoding="utf-8")
    print(f"Updated {summary_path} with retrospective sampling and outcome distribution.")

print("All enrichment and alias tasks complete.")
