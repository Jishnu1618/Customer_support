import json
import sqlite3
from pathlib import Path

db_path = Path("data/cache/twcs_index.sqlite")
knowledge_path = Path("data/processed/v2/spotify_knowledge.jsonl")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

with open(knowledge_path, "r", encoding="utf-8") as f:
    knowledge_items = [json.loads(line) for line in f]

print(f"Total knowledge items: {len(knowledge_items)}")

# Check outcomes for first 100 items
confirmed_words = ["thank", "thx", "fixed", "works now", "working now", "it worked", "got it", "solved", "perfect", "awesome", "great", "helped", "all good"]
unclear_words = ["still", "not working", "didn't work", "did not work", "doesn't work", "does not work", "same error", "already tried", "sent a dm", "dm sent", "sent dm", "messaged you"]

outcome_counts = {"confirmed": 0, "unconfirmed": 0, "unclear": 0}

for item in knowledge_items[:100]:
    brand_reply_id = item["selected_brand_reply_tweet_id"]
    reply_text = item["brand_reply_text"].lower()
    
    # Check if there are subsequent customer replies to this brand reply
    cursor.execute("SELECT tweet_id, author_id, text, inbound FROM tweets WHERE in_response_to_tweet_id = ?", (brand_reply_id,))
    followup_tweets = cursor.fetchall()
    
    if not followup_tweets:
        # No customer followup
        # If brand asked for DM, outcome is unclear
        if "dm" in reply_text or "direct message" in reply_text:
            outcome = "unclear"
        else:
            outcome = "unconfirmed"
    else:
        # There is a customer followup!
        cust_followups = [t for t in followup_tweets if t["inbound"] == 1]
        if not cust_followups:
            outcome = "unconfirmed"
        else:
            followup_text = " ".join([t["text"].lower() for t in cust_followups])
            if any(w in followup_text for w in confirmed_words):
                outcome = "confirmed"
            elif any(w in followup_text for w in unclear_words):
                outcome = "unclear"
            elif "dm" in reply_text:
                outcome = "unclear"
            else:
                outcome = "unconfirmed"
                
    outcome_counts[outcome] += 1

print("Sample 100 outcome counts:", outcome_counts)
