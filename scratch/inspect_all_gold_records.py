import json
import re

with open('gold_selection_manifest.jsonl', 'r', encoding='utf-8') as f:
    entries = [json.loads(line) for line in f]

print(f"Total entries: {len(entries)}")
subsets = {}
for e in entries:
    subsets[e['subset']] = subsets.get(e['subset'], 0) + 1
print("Subsets:", subsets)
