import json
import pandas as pd
from pathlib import Path

# Load gold manifest and labels
manifest_path = Path("gold_selection_manifest.jsonl")
labels_path = Path("gold_labels.csv")

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest_entries = {json.loads(line)["example_id"]: json.loads(line) for line in f}

df = pd.read_csv(labels_path)
df["subset"] = df["example_id"].map(lambda x: manifest_entries[x]["subset"])

print("================ TOTAL GOLD EVALUATION SUMMARY (200 EXAMPLES) ================")
print(f"Total count: {len(df)}")
print(f"Challenge count: {(df['subset'] == 'challenge').sum()}")
print(f"Random count: {(df['subset'] == 'random').sum()}")

def print_subset_stats(sub_df, name):
    print(f"\n----------------- {name} ({len(sub_df)} EXAMPLES) -----------------")
    print("Intent Distribution:")
    print(sub_df["intent"].value_counts().to_string())
    print("\nHandling Decision Distribution:")
    print(sub_df["handling_decision"].value_counts().to_string())
    print("\nNeeds Clarification Distribution:")
    print(sub_df["needs_clarification"].value_counts().to_string())
    print("\nConfidence Distribution:")
    print(sub_df["annotation_confidence"].value_counts().to_string())

print_subset_stats(df[df["subset"] == "challenge"], "CHALLENGE SUBSET")
print_subset_stats(df[df["subset"] == "random"], "RANDOM SUBSET")
print_subset_stats(df, "OVERALL COMBINED GOLD SET")

# Also write markdown summary
summary_lines = []
summary_lines.append("# Gold Evaluation Set Annotation Summary (200 Examples)\n")
summary_lines.append("Frozen Specification Version: 1.0_frozen")
summary_lines.append(f"Annotator: human_annotator_1")
summary_lines.append(f"Total Examples: 200 (150 Random + 50 Challenge | 0 Overlap)\n")

for subset_name, title in [("challenge", "50 Challenge Examples"), ("random", "150 Random Examples"), ("all", "Overall Combined Gold Set (200 Examples)")]:
    sub = df if subset_name == "all" else df[df["subset"] == subset_name]
    summary_lines.append(f"## {title}\n")
    
    summary_lines.append("### Intent Distribution")
    summary_lines.append("| Intent | Count | Percentage |")
    summary_lines.append("|---|---:|---:|")
    for intent, cnt in sub["intent"].value_counts().items():
        summary_lines.append(f"| `{intent}` | {cnt} | {cnt/len(sub)*100:.1f}% |")
    summary_lines.append("")

    summary_lines.append("### Handling Decision Distribution")
    summary_lines.append("| Handling Decision | Count | Percentage |")
    summary_lines.append("|---|---:|---:|")
    for dec, cnt in sub["handling_decision"].value_counts().items():
        summary_lines.append(f"| `{dec}` | {cnt} | {cnt/len(sub)*100:.1f}% |")
    summary_lines.append("")

    summary_lines.append("### Needs Clarification")
    summary_lines.append("| Needs Clarification | Count | Percentage |")
    summary_lines.append("|---|---:|---:|")
    for cl, cnt in sub["needs_clarification"].value_counts().items():
        summary_lines.append(f"| `{cl}` | {cnt} | {cnt/len(sub)*100:.1f}% |")
    summary_lines.append("\n---\n")

report_path = Path("results/phase2_v2/gold_annotations_summary.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(summary_lines))
print(f"Wrote summary report to {report_path}")
