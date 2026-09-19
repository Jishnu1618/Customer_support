import json
from pathlib import Path

dev_path = Path("data/processed/v2/dev_inputs.jsonl")
with open(dev_path, "r", encoding="utf-8") as f:
    dev_records = [json.loads(line) for line in f]

out_lines = []
out_lines.append(f"TOTAL DEV RECORDS: {len(dev_records)}\n")
for idx, r in enumerate(dev_records):
    out_lines.append(f"--- [{idx+1}/50] ID: {r['example_id']} | Group: {r['group_id']} ---")
    out_lines.append(f"Model Input Text:\n{r['model_input_text']}")
    out_lines.append(f"Turns count: {len(r['ancestor_turns'])}")
    out_lines.append(f"Input Flags: {json.dumps(r['input_quality_flags'])}")
    out_lines.append("")

with open("scratch/dev_50_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))

print(f"Dumped {len(dev_records)} records to scratch/dev_50_summary.txt")
