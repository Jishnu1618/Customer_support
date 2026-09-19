# Phase 2 Data Summary: Spotify Historical Corpus & Evaluation Pool

## Partition Sizes
- **Historical Corpus (`spotify_knowledge.jsonl`)**: 3,000 conversation groups (target: 3000)
- **Development Inputs (`dev_inputs.jsonl`)**: 50 customer messages (target: 50)
- **Evaluation Pool Inputs (`eval_pool_inputs.jsonl`)**: 1,000 conversation groups (target: 1000)
- **Total Partitioned Groups**: 4,050 distinct conversation groups

## Split Isolation & Leakage Verification
- **Group Overlap Across Partitions**: 0 (strictly verified; full conversation tree assigned to exactly one partition).
- **Exact Duplicate Inquiries Deduplicated**: 138 groups removed across 85 clusters.
- **Review Group Blacklist**: All 121 previously reviewed groups excluded from `eval_pool`.
- **Model Input Leakage Prevention**: In both `dev_inputs.jsonl` and `eval_pool_inputs.jsonl`, the selected brand reply is excluded from inputs.
- **Input Quality Flags**: Computed strictly from customer ancestor context; no future-reply properties are leaked into input flags.

## Language Detection & Contextual Interpretability
- **Three Explicit Language States**: `english`, `non_english`, `uncertain`
- **Scoring**: Rule-based score named `language_heuristic_score` (not presented as calibrated confidence).
- **Language State Distribution**:
  - `english`: 27,364
  - `non_english`: 230
  - `uncertain`: 985
- **Inclusion Decision Breakdown**:
  - `included_english_eligible`: 27,364
  - `excluded_uncertain_pending_review`: 985
  - `excluded_non_english`: 230
  - `excluded_uninterpretable`: 0
  - `excluded_structural_or_reference`: 66
- **Human Verification Preparation**:
  - Review queue written to `results/phase2/language_review_queue.json`.
  - Balanced review sheet prepared at `results/phase2/language_human_review_sheet.csv` with human-label columns blank.
  - Language accuracy will be reported only after actual human verification.

## Input Quality Flags Distribution (Used for Routing, Challenge Sampling & Inference)
| Input Flag | Count | Percentage |
|---|---:|---:|
| `has_url` | 664 | 16.4% |
| `private_handoff` | 15 | 0.4% |
| `external_context_required` | 8 | 0.2% |
| `suspected_multipart` | 201 | 5.0% |
| `partial_text` | 243 | 6.0% |

## Reference Reply Quality Flags Distribution (Historical Knowledge Metadata)
| Reply Flag | Count | Percentage |
|---|---:|---:|
| `has_url` | 2,217 | 54.7% |
| `private_handoff` | 989 | 24.4% |
| `external_context_required` | 82 | 2.0% |
| `suspected_multipart` | 0 | 0.0% |
| `partial_text` | 108 | 2.7% |

## Exclusions Breakdown
- Total Excluded Candidates: 1,051
- `UNCERTAIN_LANGUAGE_empty_text`: 184
- `UNCERTAIN_LANGUAGE_unrecognized_tokens_insufficient_evidence`: 173
- `UNCERTAIN_LANGUAGE_single_stopword_low_ratio`: 160
- `EXACT_DUPLICATE_INQUIRY`: 138
- `UNCERTAIN_LANGUAGE_too_short`: 135
- `NON_ENGLISH_non_english_stopwords`: 131
- `NON_ENGLISH_non_latin_script`: 27
- `UNCERTAIN_LANGUAGE_no_alphabetic_words`: 25
- `UNCERTAIN_LANGUAGE_technical_terms_no_stopwords`: 12
- `STRUCTURAL_MISSING_PARENT:14947`: 1
- `STRUCTURAL_MISSING_PARENT:41779`: 1
- `STRUCTURAL_MISSING_PARENT:199171`: 1
- `STRUCTURAL_MISSING_PARENT:203063`: 1
- `STRUCTURAL_MISSING_PARENT:283261`: 1
- `STRUCTURAL_MISSING_PARENT:289770`: 1
- `STRUCTURAL_MISSING_PARENT:365734`: 1
- `STRUCTURAL_MISSING_PARENT:371596`: 1
- `STRUCTURAL_MISSING_PARENT:407159`: 1
- `STRUCTURAL_MISSING_PARENT:431435`: 1
- `STRUCTURAL_MISSING_PARENT:448864`: 1
- `STRUCTURAL_MISSING_PARENT:620445`: 1
- `STRUCTURAL_MISSING_PARENT:643424`: 1
- `STRUCTURAL_MISSING_PARENT:709675`: 1
- `STRUCTURAL_MISSING_PARENT:723056`: 1
- `STRUCTURAL_MISSING_PARENT:782963`: 1
- `STRUCTURAL_MISSING_PARENT:798489`: 1
- `STRUCTURAL_MISSING_PARENT:839958`: 1
- `STRUCTURAL_MISSING_PARENT:847130`: 1
- `STRUCTURAL_MISSING_PARENT:859932`: 1
- `STRUCTURAL_MISSING_PARENT:962312`: 1
- `STRUCTURAL_MISSING_PARENT:1087972`: 1
- `STRUCTURAL_MISSING_PARENT:1096204`: 1
- `STRUCTURAL_MISSING_PARENT:1109996`: 1
- `STRUCTURAL_MISSING_PARENT:1189539`: 1
- `STRUCTURAL_MISSING_PARENT:1197648`: 1
- `STRUCTURAL_MISSING_PARENT:1199852`: 1
- `STRUCTURAL_MISSING_PARENT:1222464`: 1
- `STRUCTURAL_MISSING_PARENT:1229819`: 1
- `STRUCTURAL_MISSING_PARENT:1280116`: 1
- `STRUCTURAL_MISSING_PARENT:1349647`: 1
- `STRUCTURAL_MISSING_PARENT:1455463`: 1
- `STRUCTURAL_MISSING_PARENT:1462718`: 1
- `STRUCTURAL_MISSING_PARENT:1474855`: 1
- `STRUCTURAL_MISSING_PARENT:1531541`: 1
- `STRUCTURAL_MISSING_PARENT:1635377`: 1
- `STRUCTURAL_MISSING_PARENT:1773086`: 1
- `STRUCTURAL_MISSING_PARENT:1778461`: 1
- `STRUCTURAL_MISSING_PARENT:1797080`: 1
- `STRUCTURAL_MISSING_PARENT:1808944`: 1
- `STRUCTURAL_MISSING_PARENT:1813809`: 1
- `STRUCTURAL_MISSING_PARENT:1851256`: 1
- `STRUCTURAL_MISSING_PARENT:1858045`: 1
- `STRUCTURAL_MISSING_PARENT:1920585`: 1
- `STRUCTURAL_MISSING_PARENT:1933737`: 1
- `STRUCTURAL_MISSING_PARENT:1956873`: 1
- `STRUCTURAL_MISSING_PARENT:1966392`: 1
- `STRUCTURAL_MISSING_PARENT:1982579`: 1
- `STRUCTURAL_MISSING_PARENT:1995978`: 1
- `STRUCTURAL_MISSING_PARENT:2042300`: 1
- `STRUCTURAL_MISSING_PARENT:2042831`: 1
- `STRUCTURAL_MISSING_PARENT:2058831`: 1
- `STRUCTURAL_MISSING_PARENT:2114150`: 1
- `STRUCTURAL_MISSING_PARENT:2114197`: 1
- `STRUCTURAL_MISSING_PARENT:2116886`: 1
- `STRUCTURAL_MISSING_PARENT:2317063`: 1
- `STRUCTURAL_MISSING_PARENT:2439881`: 1
- `STRUCTURAL_MISSING_PARENT:2442031`: 1
- `STRUCTURAL_MISSING_PARENT:2668074`: 1
- `STRUCTURAL_MISSING_PARENT:2721862`: 1
- `STRUCTURAL_MISSING_PARENT:2780803`: 1
- `STRUCTURAL_MISSING_PARENT:2846496`: 1
- `STRUCTURAL_MISSING_PARENT:2916595`: 1
- `STRUCTURAL_MISSING_PARENT:2926304`: 1
- `STRUCTURAL_MISSING_PARENT:2970811`: 1
- `STRUCTURAL_MISSING_PARENT:2973968`: 1
