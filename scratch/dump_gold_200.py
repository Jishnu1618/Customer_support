import json
from pathlib import Path

manifest_path = Path("gold_selection_manifest.jsonl")
with open(manifest_path, "r", encoding="utf-8") as f:
    entries = [json.loads(line) for line in f]

print(f"Total entries: {len(entries)}")
challenge_entries = [e for e in entries if e["subset"] == "challenge"]
random_entries = [e for e in entries if e["subset"] == "random"]

print(f"Challenge entries: {len(challenge_entries)}")
print(f"Random entries: {len(random_entries)}")

# Write summary of all 200 records for inspection
lines = []
lines.append(f"TOTAL EVALUATION SELECTION: {len(entries)} (50 Challenge + 150 Random)\n")

lines.append("=================== 50 CHALLENGE EXAMPLES ===================")
for idx, e in enumerate(challenge_entries):
    lines.append(f"\n--- [CHALLENGE {idx+1}/50] {e['example_id']} ---")
    lines.append(f"Challenge reasons: {e['challenge_reasons']} (Score: {e['challenge_score']})")
    lines.append(f"Turns count: {len(e['ancestor_turns'])}")
    lines.append(f"Input Flags: {e['input_quality_flags']}")
    lines.append(f"Model Input Text:\n{e['model_input_text']}")

lines.append("\n\n=================== 150 RANDOM EXAMPLES ===================")
for idx, e in enumerate(random_entries):
    lines.append(f"\n--- [RANDOM {idx+1}/150] {e['example_id']} ---")
    lines.append(f"Turns count: {len(e['ancestor_turns'])}")
    lines.append(f"Input Flags: {e['input_quality_flags']}")
    lines.append(f"Model Input Text:\n{e['model_input_text']}")

with open("scratch/gold_200_inspection.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Dumped all 200 records to scratch/gold_200_inspection.txt")
