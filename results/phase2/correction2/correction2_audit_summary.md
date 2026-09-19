# Correction 2 Audit Report: Complete Duplicate Detection & Evaluation Isolation

## 1. Executive Summary
- **Full Eligible Groups Examined**: 27,651
- **Search Limitations Removed**: 500-candidate cap and 100-comparison window removed. 100% of eligible candidates evaluated.
- **Inverted Index Performance**: Prefix and length filtered search across 27k candidates completed in seconds.
- **Duplicate Pairs Detected**: 520 pairs (433 exact, 87 near).
- **Multi-Member Duplicate Clusters**: 152 clusters containing 410 conversation groups.
- **Evaluation Restriction Propagation**: Fixed. Any cluster member with review or development exposure marks the entire cluster and its canonical representative ineligible for evaluation.

---

## 2. Detection of Previously Missed Pairs
Both known pairs that previously spanned evaluation and historical partitions are now successfully detected:
1. **Pair 1**: Group `2544106` (eval) ↔ Group `779665` (historical)
   - Detected: **True**
   - Details: `('2544106', '779665', 1.0, 'exact')`
2. **Pair 2**: Group `1739407` (eval) ↔ Group `1544644` (historical)
   - Detected: **True**
   - Details: `('1544644', '1739407', 0.9524, 'near')`

---

## 3. Evaluation Exclusion Sources & Counts (No Hardcoded Counts)
| Source File | SHA256 (prefix) | Unique Roots Contributed |
|---|---|---:|
| `original_sampling_manifest.json` | `b3087587be98...` | 31 |
| `sampling_manifest_original_uploaded.json` | `b3087587be98...` | 31 |
| `sampling_manifest_v1.json` | `100a607c3fcd...` | 30 |
| `sampling_manifest.json` | `d0ac2d9cc582...` | 30 |
| `review_scores.csv` | `4447e61475fd...` | 90 |
| `dev_inputs.jsonl` | `f590fa5811fb...` | 50 |

- **Total Unique Reviewed Roots**: 121
- **Total Development Group IDs**: 50
- **Total Restricted Roots for Evaluation**: 171

---

## 4. Existing 4,050 Exported Records Audit
- **Exported Records Examined**: 4,050
- **Duplicate Pairs Found Among Exported**: 2
- **Cross-Partition Duplicate Clusters Found**: 2
  - In the currently exported production records (prior to full regeneration), 2 near-duplicate clusters span partitions (e.g. eval_pool and historical) due to previous window/sample caps.
  - Production dataset files are preserved as instructed; final regeneration will occur after all corrections are verified.

---

## 5. Duplicate Detection & Matching Rules
1. **Exact Duplicate Rule**: Normalized inquiry strings after lowercase, URL/handle removal, punctuation strip, and whitespace collapse.
2. **Near-Duplicate Rule**: Token Jaccard similarity >= 0.85 evaluated via an inverted index with prefix and length filtering.
3. **Negation Guard**: Pairs with conflicting negation tokens (`not`, `no`, `never`, `cant`, `cannot`, etc.) are prohibited from merging.
4. **Error Code Guard**: Pairs with conflicting error codes (e.g. `404` vs `500` or hex codes) are prohibited from merging.
5. **Generic Short Message Guard**: Short replies (<= 3 words or generic phrases such as "Still broken", "Thank you") incorporate allowed customer ancestor context turns to prevent merging distinct support issues.
6. **Transitive Clustering**: Connected components algorithm groups all transitively connected pairs (A ↔ B and B ↔ C => {A, B, C}).
7. **Stable Deterministic Canonical IDs**: Each cluster is assigned `cluster_{canonical_id}` where canonical is the minimum group ID by deterministic integer/alphanumeric ordering.
