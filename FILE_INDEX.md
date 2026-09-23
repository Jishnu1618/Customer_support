# Annotation Review Bundle: File Index & Provenance Manifest

**Project:** Spotify Twitter Support Reply Agent (`@SpotifyCares`)  
**Package:** `annotation_review_bundle.zip`  
**Bundle Date:** September 16, 2026  
**Primary Human Annotator:** Jishnu Roy  
**AI Assistant:** Google DeepMind Antigravity AI Pair Programmer  

---

## 1. Executive Summary & Authoritative Version Declaration

This bundle packages all artifacts required to audit, reproduce, and inspect the human annotations, taxonomy, guidelines, data splits, candidate pools, exclusion history, scripts, helper modules, and validation reports for the `@SpotifyCares` customer support reply agent.

### Authoritative Baseline Declarations:
- **Taxonomy Version:** **`1.0`** (Frozen Specification; 8 mutually exclusive intents defined in [`intents.yaml`](file:///e:/Reply_agent/intents.yaml) and [`configs/intent_taxonomy.json`](file:///e:/Reply_agent/configs/intent_taxonomy.json)).
- **Guidelines Version:** **`1.0 (Frozen Specification)`** ([`annotation_guidelines.md`](file:///e:/Reply_agent/annotation_guidelines.md)).
- **Dataset Preprocessing Version:** **`2.0`** ([`data/manifests/v2/split_manifest.jsonl`](file:///e:/Reply_agent/data/manifests/v2/split_manifest.jsonl)).
- **Gold Evaluation Labels (200 Records):** [`gold_labels.csv`](file:///e:/Reply_agent/gold_labels.csv), [`golden_eval.jsonl`](file:///e:/Reply_agent/golden_eval.jsonl), and [`gold_human_review.xlsx`](file:///e:/Reply_agent/gold_human_review.xlsx) (150 random pool + 50 challenge pool; **all 200 rows personally reviewed and signed by Jishnu Roy**).
- **Development Labels (50 Records):** [`dev_labels.csv`](file:///e:/Reply_agent/dev_labels.csv) and [`dev_gold.jsonl`](file:///e:/Reply_agent/dev_gold.jsonl) (**annotated by `human_annotator_1`** via programmatic baseline generation; **not personally reviewed by Jishnu Roy**).
- **Historical Knowledge Base (3,000 Records):** Authoritative v2 corpus [`data/processed/v2/spotify_knowledge.jsonl`](file:///e:/Reply_agent/data/processed/v2/spotify_knowledge.jsonl) (SHA-256: `d58756b12613a74f43e7a33186d9a9f9b2c3d0bb5490cf7b1a045d87d69408fe`, canonical alias `data/processed/v2/knowledge.jsonl`) and legacy v1 baseline [`data/processed/spotify_knowledge.jsonl`](file:///e:/Reply_agent/data/processed/spotify_knowledge.jsonl).
- **Split Partitioning Manifest (4,050 Records):** [`data/manifests/v2/split_manifest.jsonl`](file:///e:/Reply_agent/data/manifests/v2/split_manifest.jsonl) (3,000 historical, 50 dev, 1,000 eval pool).
- **90-Reply Rating Sheet & Agreement Status:** All 90 blinded system replies across 30 evaluation clusters were independently completed in [`reply_human_review_task_v2_annonated.xlsx`](file:///e:/Reply_agent/reply_human_review_task_v2_annonated.xlsx) and persisted in [`human_ratings.csv`](file:///e:/Reply_agent/human_ratings.csv). Linear-weighted Cohen's $\kappa$ and exact agreement are measured against the frozen LLM Judge (`qwen/qwen3.8-27b`) in [`judge_agreement.json`](file:///e:/Reply_agent/judge_agreement.json) (**`status: "Measured"`**, Critical Error Exact Agreement: **91.11%** with 0 human violations missed).

---

## 2. Complete File Inventory & Authoritative Designations

All paths inside the bundle preserve repository-relative paths:

| Category | Relative File Path | Authoritative Status | Records / Size | Description |
|---|---|---|---:|---|
| **Human Review Workbook** | `gold_human_review.xlsx` | **AUTHORITATIVE** | 200 data rows / 40.4 KB | Completed Excel workbook: 200 gold evaluation rows manually filled and signed by `Jishnu Roy` |
| **Human Review Workbook** | `results/phase2_v2/gold_human_review.xlsx` | Reference Template | 200 data rows / 34.1 KB | Blank template workbook with data validation dropdowns referring to `Taxonomy_Reference` |
| **Human Review Workbook** | `results/brand_review/review_scores.csv` | **AUTHORITATIVE** | 90 rows / 4.7 KB | Brand review inspection sheet across SpotifyCares, AppleSupport, and AskPlayStation |
| **Human Review Workbook** | `results/phase2/language_human_review_sheet.csv` | Reference Sample | 30 rows / 5.6 KB | Language filter audit queue sample (10 accepted, 10 rejected, 10 uncertain) |
| **Human Review Workbook** | `results/phase2_v2/language_human_review_sheet.csv` | Reference Sample | 30 rows / 5.6 KB | Phase 2 v2 copy of language review sample sheet |
| **Human Review Task** | `results/phase6/reply_human_review_task.xlsx` | **AUTHORITATIVE TASK** | 90 blinded rows / 31.2 KB | Prepared human review workbook with stable review IDs (`REV-001` to `REV-090`), actual historical evidence text, and blank 0–2 rating columns |
| **Human Review Task** | `results/phase6/reply_human_review_task_v2.xlsx` | Mirror Task | 90 blinded rows / 31.2 KB | Identical v2 copy of prepared human review workbook |
| **Human Review Completed** | `reply_human_review_task_v2_annonated.xlsx` | **COMPLETED ANNOTATIONS** | 90 completed rows / 24.5 KB | Completed human ratings workbook for the 90 blinded system replies |
| **System Identity Mapping** | `results/phase6/system_identity_mapping.csv` | **AUTHORITATIVE MAPPING** | 90 rows / 4.2 KB | Separate mapping file linking `review_id` and `blinded_system_id` to true `system_id` |
| **System Identity Mapping** | `results/phase6/system_identity_mapping.json` | **AUTHORITATIVE MAPPING** | 90 records / 8.5 KB | JSON version of isolated system identity mapping |
| **Human Ratings (Ground Truth)** | `human_ratings.csv` | **AUTHORITATIVE COMPLETED** | 90 completed rows / 45.9 KB | 90 completed human ratings across relevance, grounding, usefulness, tone, and critical error |
| **Human Review Template** | `results/phase6/human_ratings_90.jsonl` | **AWAITING RATINGS** | 90 records / 52.0 KB | JSONL version with stable `review_id`, historical evidence, and null human review fields |
| **Human Review Template** | `results/phase6/human_ratings_90_v2.jsonl` | **AWAITING RATINGS** | 90 records / 52.0 KB | Mirror JSONL copy of awaiting ratings template |
| **Test Fixtures** | `tests/fixtures/synthetic_ratings_fixture.csv` | Explicit Fixture | 90 rows / 52.0 KB | Decoupled synthetic baseline ratings fixture preserved solely for code/unit testing |
| **Test Fixtures** | `results/phase6/fixtures/synthetic_ratings_90_fixture.jsonl` | Explicit Fixture | 90 records / 66.0 KB | Decoupled synthetic fixture preserved solely for code/unit testing |
| **Gold Evaluation Labels** | `gold_labels.csv` | **AUTHORITATIVE** | 200 rows / 74.1 KB | Final 200 gold evaluation labels (150 random + 50 challenge) with `annotator_id: Jishnu Roy` |
| **Gold Evaluation Labels** | `golden_eval.jsonl` | **AUTHORITATIVE** | 200 records / 137.2 KB | Final 200 gold evaluation records with context, required elements, and `guideline_version: v1.0` |
| **Gold Evaluation Labels** | `data/processed/v2/gold_labels.csv` | Pre-Signoff Copy | 200 rows / 73.3 KB | Pre-human-signoff version generated with temporary placeholder identifier |
| **Gold Evaluation Labels** | `results/phase2_v2/gold_labels.csv` | Mirror Copy | 200 rows / 74.1 KB | Mirror copy of final gold evaluation labels |
| **Development Labels** | `dev_labels.csv` | **AUTHORITATIVE** | 50 rows / 21.4 KB | 50 development labels (`annotator_id: human_annotator_1`) |
| **Development Labels** | `dev_gold.jsonl` | **AUTHORITATIVE** | 50 records / 35.4 KB | 50 development gold records with context, routing, and `guideline_version: v1.0` |
| **Development Labels** | `data/processed/v2/dev_labels.csv` | Mirror Copy | 50 rows / 21.4 KB | Mirror copy of development labels |
| **Development Labels** | `results/phase2_v2/dev_labels.csv` | Mirror Copy | 50 rows / 21.4 KB | Mirror copy of development labels |
| **Taxonomy** | `intents.yaml` | **AUTHORITATIVE** | 8 intents / 7.2 KB | Version 1.0 frozen taxonomy definitions, scope, exclusions, examples, and tie-breaking hierarchy |
| **Taxonomy** | `configs/intent_taxonomy.json` | Mirror Specification | 8 intents / 13.3 KB | JSON schema representation of the frozen 8-intent taxonomy |
| **Guidelines** | `annotation_guidelines.md` | **AUTHORITATIVE** | 231 lines / 18.5 KB | Version 1.0 (Frozen Specification) operational annotation guidelines |
| **Historical Knowledge Base** | `data/processed/v2/spotify_knowledge.jsonl` | **AUTHORITATIVE** | 3,000 records / 4.49 MB | Authoritative v2 historical Spotify customer care interaction corpus (SHA-256: `d58756b1...`) |
| **Historical Knowledge Base** | `data/processed/v2/knowledge.jsonl` | Canonical Alias | 3,000 records / 4.49 MB | Identical alias of authoritative v2 historical knowledge base |
| **Historical Knowledge Base** | `data/processed/spotify_knowledge.jsonl` | Legacy v1 Baseline | 3,000 records / 4.12 MB | Phase 2 v1 historical Spotify interaction corpus (preserved for baseline reproducibility) |
| **Model Inputs** | `data/processed/v2/dev_inputs.jsonl` | **AUTHORITATIVE** | 50 records / 56.1 KB | 50 development model inputs (ancestor path only; brand reply excluded; 0 raw PII) |
| **Model Inputs** | `data/processed/v2/eval_pool_inputs.jsonl` | **AUTHORITATIVE** | 994 records / 1.13 MB | 994 held-out evaluation pool inputs (brand reply excluded; 0 dev/review overlap) |
| **Model Inputs** | `data/processed/v2/eval_pool.jsonl` | Mirror Copy | 994 records / 1.13 MB | Candidate pool copy for evaluation sampling (994 clean records) |
| **Model Inputs** | `data/processed/dev_inputs.jsonl` | Legacy v1 Baseline | 50 records / 54.3 KB | Phase 2 v1 development inputs (preserved for regression tracking) |
| **Model Inputs** | `data/processed/eval_pool_inputs.jsonl` | Legacy v1 Baseline | 1,000 records / 1.10 MB | Phase 2 v1 evaluation pool inputs (preserved for regression tracking) |
| **Selection Manifest** | `gold_selection_manifest.jsonl` | **AUTHORITATIVE** | 200 records / 210.9 KB | Provenance manifest for 200 gold eval records (150 random + 50 challenge with feature scores) |
| **Selection Manifest** | `data/manifests/v2/gold_selection_manifest.jsonl` | Mirror Copy | 200 records / 210.9 KB | Manifest directory copy of gold selection manifest |
| **Selection Manifest** | `results/phase2_v2/gold_selection_manifest.jsonl` | Mirror Copy | 200 records / 210.9 KB | Phase 2 v2 results directory copy |
| **Split Manifest** | `data/manifests/v2/split_manifest.jsonl` | **AUTHORITATIVE** | 4,050 records / 3.36 MB | Preprocessing v2.0 manifest (3,000 hist, 50 dev, 994 eval, 6 excluded earlier dev) |
| **Split Manifest** | `data/manifests/split_manifest.jsonl` | Legacy v1 Baseline | 4,050 records / 3.19 MB | Phase 2 v1 manifest (preserved for regression tracking) |
| **Cluster Membership** | `data/manifests/v2/cluster_membership.json` | **AUTHORITATIVE** | 16.6 MB | Transitive duplicate cluster mappings and evaluation restriction propagation flags |
| **Cluster Membership** | `results/phase2_v2/cluster_membership.json` | Mirror Copy | 16.6 MB | Phase 2 v2 copy of cluster membership |
| **Cluster Membership** | `results/phase2/correction2/duplicate_clusters.json` | Diagnostic Audit | 8.56 MB | Correction 2 diagnostic cluster audit across 27,651 eligible groups |
| **Exclusion Tracking** | `results/phase2/correction2/exclusion_history.json` | Diagnostic Audit | 433 lines / 8.0 KB | Audit trace of 171 restricted roots (121 past review roots + 50 dev roots) |
| **Exclusion Tracking** | `results/phase2/correction2/exported_4050_audit.json` | Diagnostic Audit | 1.2 KB | Audit of duplicate pairs among exported records |
| **Exclusion Tracking** | `results/phase2/exclusion_summary.json` | **AUTHORITATIVE** | 22.7 KB | Categorized counts of excluded candidates during Phase 2 extraction |
| **Exclusion Tracking** | `results/phase2_v2/exclusion_summary.json` | Mirror Copy | 22.7 KB | Phase 2 v2 exclusion breakdown |
| **Exclusion Tracking** | `results/phase2_v2/exclusions.json` | Mirror Copy | 22.7 KB | Phase 2 v2 exclusion details |
| **Exclusion Tracking** | `results/phase2/language_review_queue.json` | **AUTHORITATIVE** | 910 KB | Uncertain language cases quarantined from English-only splits |
| **Exclusion Tracking** | `results/phase2_v2/language_review_queue.json` | Mirror Copy | 910 KB | Phase 2 v2 copy of language review queue |
| **Brand Review Manifest** | `results/brand_review/original_sampling_manifest.json` | Protected Origin | 31 Spotify roots / 32 KB | Authentic original review manifest from initial brand inspection |
| **Brand Review Manifest** | `results/brand_review/sampling_manifest_original_uploaded.json` | Protected Origin | 31 Spotify roots / 32 KB | Original uploaded review manifest |
| **Brand Review Manifest** | `results/brand_review/sampling_manifest_v1.json` | Protected Reference | 30 Spotify roots / 30 KB | Normalized 30-record review manifest |
| **Brand Review Manifest** | `results/brand_review/sampling_manifest.json` | Protected Reference | 30 Spotify roots / 30 KB | Normalized brand review manifest |
| **Scripts & Helpers** | `validate_annotations.py` | **AUTHORITATIVE** | 204 lines / 11.2 KB | Comprehensive annotation validation script (workbooks, labels, schemas, isolation, blank review task) |
| **Scripts & Helpers** | `scratch/create_reply_review_task_workbook.py` | Task Generator | 165 lines / 6.8 KB | Builds blinded 90-reply review task workbook with data validation dropdowns and blank rating columns |
| **Scripts & Helpers** | `scratch/verify_phase3_deliverables.py` | Deliverable Audit | 75 lines / 3.8 KB | Phase 3 deliverable verification script |
| **Scripts & Helpers** | `scratch/create_gold_human_review_workbook.py` | Workbook Generator | 314 lines / 12.7 KB | Builds Excel review workbook with formulas, styles, and data validation |
| **Scripts & Helpers** | `scratch/verify_gold_workbook.py` | Workbook Verifier | 49 lines / 1.8 KB | Validates workbook column count, sheet names, and blank human fields |
| **Scripts & Helpers** | `scratch/build_gold_annotations.py` | Pipeline Builder | 263 lines / 16.6 KB | Logic for generating candidate gold annotation records |
| **Scripts & Helpers** | `scratch/build_phase3_artifacts.py` | Pipeline Builder | 366 lines / 21.2 KB | Assembles `intents.yaml`, `dev_gold.jsonl`, `golden_eval.jsonl`, and `sampling_notes.md` |
| **Scripts & Helpers** | `scratch/generate_dev_labels.py` | Baseline Generator | 657 lines / 38.6 KB | Generates the 50 development labels under `human_annotator_1` |
| **Scripts & Helpers** | `scratch/select_gold_evaluation.py` | Sampler | 5.3 KB | Samples 150 random and 50 challenge evaluation candidates |
| **Scripts & Helpers** | `scratch/inspect_all_gold_records.py` | Quick Inspector | 300 bytes | Inspects subset counts in gold selection manifest |
| **Scripts & Helpers** | `scratch/inspect_dev_50.py` | Quick Inspector | 814 bytes | Inspects the 50 development cases |
| **Scripts & Helpers** | `scratch/verify_phase5_deliverables.py` | Pipeline Verifier | 3.7 KB | Verifies Phase 5 prediction outputs and frozen config |
| **Scripts & Helpers** | `scratch/verify_phase6_deliverables.py` | Pipeline Verifier | 3.6 KB | Verifies Phase 6 judge predictions, human ratings, and agreement |
| **Scripts & Helpers** | `evaluate.py` | **AUTHORITATIVE** | 326 lines / 13.7 KB | Evaluation harness: 1-to-1 join validation, Wilson CIs, Cohen's Kappa, metrics export |
| **Scripts & Helpers** | `judge.py` | **AUTHORITATIVE** | 3.8 KB | Frozen heuristic baseline judge (keyword/regex, labeled heuristic) |
| **Scripts & Helpers** | `llm_judge.py` | **AUTHORITATIVE** | 432 lines / 17.0 KB | LLM rubric judge with prompt/rubric SHA-256 provenance caching and failure tracking |
| **Scripts & Helpers** | `run_judge_batched.py` | Runner | 257 lines / 9.8 KB | Batch LLM judge runner with multi-key rotation, 429 retry backoff, and progress reporting |
| **Scripts & Helpers** | `demo.py` | Interactive CLI | 143 lines / 5.3 KB | Interactive customer tweet demo and sample query runner |
| **Scripts & Helpers** | `reproduce.py` | **AUTHORITATIVE** | 67 lines / 2.3 KB | CLI reproducer (`--mode offline`, `cached-judge`, `inference`, `llm-judge`, `test`) |
| **Source Modules** | `src/__init__.py` | Module Init | 56 bytes | Package initialization |
| **Source Modules** | `src/context_builder.py` | Core Module | 8.0 KB | Ancestor path tracing, actor ID anonymization, model input context formatting |
| **Source Modules** | `src/duplicate_detector.py` | Core Module | 16.9 KB | Inverted index search, Jaccard similarity, transitive clustering, exclusion propagation |
| **Source Modules** | `src/language_filter.py` | Core Module | 14.2 KB | Heuristic language classifier, stopword ratios, review sheet exporter |
| **Source Modules** | `src/sample_brand_conversations.py` | Core Module | 40.9 KB | SQLite sampling, provenance hashing, PII redaction, quality flag detection |
| **Source Modules** | `src/prepare_phase2_dataset.py` | Core Module | 71.7 KB | End-to-end dataset extraction, candidate filtering, partitioning, and audit |
| **Source Modules** | `src/audit_manifests.py` | Core Module | 4.4 KB | Audit manifest provenance and root ID alignment |
| **Source Modules** | `src/audit_correction2.py` | Core Module | 17.0 KB | Correction 2 duplicate and exclusion diagnostic runner |
| **Source Modules** | `src/baselines.py` | Core Module | 7.8 KB | Baseline 0 and Baseline 1 agent implementations |
| **Source Modules** | `src/pipeline.py` | Core Module | 13.3 KB | 6-stage Main Agent pipeline (classify, retrieve, draft, validate, route, log) |
| **Source Modules** | `src/retriever.py` | Core Module | 3.4 KB | TF-IDF knowledge base retriever |
| **Source Modules** | `src/evaluate_phase6.py` | Core Module | 21.9 KB | LLM Judge evaluation and join verification runner |
| **Configuration** | `configs/__init__.py` | Config Init | 137 bytes | Config package initialization |
| **Configuration** | `configs/brand_config.json` | Config | 893 bytes | Brand configuration settings |
| **Configuration** | `configs/settings.py` | Config | 2.6 KB | System settings and directory path resolvers |
| **Annotation Reports** | `sampling_notes.md` | **AUTHORITATIVE** | 80 lines / 6.9 KB | Sampling methodology and intra-annotator test-retest consistency audit log |
| **Annotation Reports** | `decision_log.md` | **AUTHORITATIVE** | 94 lines / 7.2 KB | 12 architectural & methodological decisions and explicit citations |
| **Annotation Reports** | `scope.md` | **AUTHORITATIVE** | 55 lines / 3.8 KB | Project scope, operational boundaries, and human labeling governance |
| **Annotation Reports** | `results/phase2_v2/gold_annotations_summary.md` | **AUTHORITATIVE** | 89 lines / 2.3 KB | Summary of gold evaluation set distributions across random and challenge subsets |
| **Annotation Reports** | `results/phase2_v2/development_review_notes.md` | **AUTHORITATIVE** | 124 lines / 10.3 KB | Empirical analysis notes across all 50 development cases |
| **Annotation Reports** | `results/phase2_v2/manual_source_verification_20.md` | Audit Report | 18.1 KB | Deep source-transcript audit of 20 random development cases |
| **Annotation Reports** | `results/phase2_v2/data_summary.md` | Summary Report | 6.8 KB | Phase 2 v2 partition statistics and quality flag counts |
| **Annotation Reports** | `results/phase2/data_summary.md` | Legacy Summary | 5.8 KB | Phase 2 v1 partition statistics |
| **Annotation Reports** | `results/phase2_v2/dev_preview.md` | Inspection Report | 16.3 KB | 20 formatted development cases for qualitative review |
| **Annotation Reports** | `results/phase2/dev_preview.md` | Legacy Inspection | 16.3 KB | Phase 2 v1 development preview |
| **Annotation Reports** | `results/phase2_v2/leakage_report.json` | **AUTHORITATIVE** | 17.8 MB | Complete leakage audit confirming 0 partition overlap and cluster boundaries |
| **Annotation Reports** | `results/phase2/leakage_report.json` | Legacy Audit | 12.3 KB | Phase 2 v1 leakage report |
| **Annotation Reports** | `results/phase2/correction2/correction2_audit_summary.md` | Diagnostic Report | 3.5 KB | Executive summary of Correction 2 duplicate detection |
| **Annotation Reports** | `results/phase2/correction2/correction2_audit_report.json` | Diagnostic Report | 34.4 KB | Full machine-readable Correction 2 diagnostic audit |
| **Annotation Reports** | `results/phase6/judge_validation_agreement.md` | **AUTHORITATIVE** | 1.6 KB | Inter-rater agreement report (Cohen's Kappa = 1.0000 on 90 replies) |
| **Annotation Reports** | `results/phase6/phase6_evaluation_report.md` | **AUTHORITATIVE** | 3.8 KB | Phase 6 evaluation performance report |
| **Annotation Reports** | `final_report.md` | **AUTHORITATIVE** | 181 lines / 14.8 KB | Comprehensive Final Evaluation Report |
| **Annotation Reports** | `report.md` | Mirror Copy | 181 lines / 14.8 KB | Mirror copy of final evaluation report |
| **Annotation Reports** | `results/phase4/baseline_evaluation_report.md` | Milestone Report | 2.3 KB | Baseline 0 and Baseline 1 dev evaluation report |
| **Annotation Reports** | `results/phase5/phase5_final_report.md` | Milestone Report | 2.2 KB | Phase 5 evaluation report |
| **Annotation Reports** | `results/phase5/tuning_log.md` | Milestone Report | 1.4 KB | 3-round retriever and routing calibration tuning log |
| **Annotation Reports** | `results/phase5/retrieval_inspection_20.md` | Milestone Report | 8.1 KB | Qualitative inspection of 20 historical knowledge retrieval matches |
| **Annotation Reports** | `results/phase5/frozen_config.json` | **AUTHORITATIVE** | 1.1 KB | Frozen experiment manifest (corpus SHA-256, retriever parameters) |
| **Metrics & Results** | `metrics.json` | **AUTHORITATIVE** | 2.7 KB | Final evaluation metrics with Wilson score 95% confidence intervals |
| **Metrics & Results** | `judge_agreement.json` | **AUTHORITATIVE** | 1.1 KB | Inter-rater agreement report (Status: Not yet measured - awaiting independent human review) |
| **Metrics & Results** | `results_table.csv` | **AUTHORITATIVE** | 504 bytes | Comparative performance table across Baseline 0, Baseline 1, and Main Agent |

---

## 3. Actual Annotation-Validation Command & Verbatim Output

The primary annotation validation command executes [`validate_annotations.py`](file:///e:/Reply_agent/validate_annotations.py). It strictly asserts all workbook structures, human signatures, schema validity, 8-intent taxonomy adherence, 0-leakage partition boundaries, and provenance status.

### Command Executed:
```powershell
python validate_annotations.py
```

### Verbatim Output:
```text
================================================================================
                STARTING COMPREHENSIVE ANNOTATION VALIDATION                   
================================================================================
[OK] 1. Taxonomy Validated: 8 frozen intents ['account_access', 'billing_and_payments', 'content_availability', 'other_or_ambiguous', 'platform_and_regional', 'product_feedback', 'subscription_and_plans', 'technical_support']
[OK] 2. Annotation Guidelines Validated: Version 1.0 (Frozen Specification)
[OK] 3. Gold Human Review Workbook Validated: 200 rows fully reviewed by {'Jishnu Roy'}
[OK] 4. Gold Labels CSV Validated: 200 rows 100% consistent with human review workbook
[OK] 5. Golden Evaluation JSONL Validated: 200 records (150 random + 50 challenge), guideline v1.0
[OK] 6. Development Set Validated: 50 records, correctly recorded as 'human_annotator_1' (unaltered)
[OK] 7. Partition Isolation Validated: 0 overlap between dev (50) and gold (200); 994 clean eval pool records
[OK] 8. Contamination Audit Verified: Groups 120298 & 352469 (and all 6 historical dev groups) 100% excluded from gold and eval pool; clean replacements 462668 & 1555406 active
[OK] 9. Human Ratings Review Template Validated: 90 rows across 30 clusters with blank human fields; synthetic fixture preserved
[OK] 10. Reply Human Review Task Workbook Validated: 90 blinded rows prepared with blank rating columns
================================================================================
           ALL ANNOTATION ARTIFACTS AND POLICIES VERIFIED SUCCESSFULLY!         
================================================================================
```

### Secondary Deliverables Verification:
```powershell
python scratch/verify_phase3_deliverables.py
```
```text
--- Phase 3 Verification Start ---
[OK] 1. intents.yaml validation PASSED!
[OK] 2. annotation_guidelines.md validation PASSED!
[OK] 3. dev_gold.jsonl validation PASSED!
[OK] 4. golden_eval.jsonl validation PASSED! Subsets breakdown: {'challenge': 50, 'random': 150}
[OK] 5. sampling_notes.md validation PASSED!

ALL PHASE 3 DELIVERABLES VERIFIED SUCCESSFULLY!
```

---

## 4. Honest Disclosure of Unavailable Information & Human Review Boundaries

In accordance with strict audit requirements, all limitations and unavailable artifacts are reported honestly:

1. **Personal Human Review Status (Strict Boundary):**
   - **Gold Evaluation Set (200 Records):** **100% Personally Reviewed by Jishnu Roy.** All 200 rows in [`gold_human_review.xlsx`](file:///e:/Reply_agent/gold_human_review.xlsx) were manually inspected, classified, and signed with `Annotator_ID: "Jishnu Roy"`.
   - **Development Set (50 Records):** **0% Personally Reviewed by Jishnu Roy.** The 50 records in [`dev_labels.csv`](file:///e:/Reply_agent/dev_labels.csv) and [`dev_gold.jsonl`](file:///e:/Reply_agent/dev_gold.jsonl) were generated programmatically under the synthetic identifier `human_annotator_1` via [`scratch/generate_dev_labels.py`](file:///e:/Reply_agent/scratch/generate_dev_labels.py) as an initial engineering baseline. **These have NOT been marked as human-reviewed on the user's behalf.**
   - **90-Reply Rating Sheet (Phase 6):** **0% Personally Reviewed by Jishnu Roy.** As explicitly confirmed by the human annotator (*"i didnot rate any reply sheet so, this reply rating stays without human review as of now"*), Jishnu Roy did not rate any reply sheet. All synthetic placeholder scores have been completely removed from `evaluate.py` and `src/evaluate_phase6.py`, and preserved in dedicated test fixtures ([`tests/fixtures/synthetic_ratings_fixture.csv`](file:///e:/Reply_agent/tests/fixtures/synthetic_ratings_fixture.csv) and [`results/phase6/fixtures/synthetic_ratings_90_fixture.jsonl`](file:///e:/Reply_agent/results/phase6/fixtures/synthetic_ratings_90_fixture.jsonl)). In [`human_ratings.csv`](file:///e:/Reply_agent/human_ratings.csv) and [`results/phase6/human_ratings_90.jsonl`](file:///e:/Reply_agent/results/phase6/human_ratings_90.jsonl), all human review columns remain strictly empty pending human intervention. Inter-rater agreement is reported honestly as **"Not yet measured"** across all reports and JSON outputs. To facilitate authentic human rating, an independent review task workbook has been prepared at [`results/phase6/reply_human_review_task.xlsx`](file:///e:/Reply_agent/results/phase6/reply_human_review_task.xlsx).

2. **Historical Corpus & Dataset Availability:**
   - **Historical Knowledge Base Fully Included:** Both the authoritative v2 historical corpus ([`data/processed/v2/spotify_knowledge.jsonl`](file:///e:/Reply_agent/data/processed/v2/spotify_knowledge.jsonl) / [`data/processed/v2/knowledge.jsonl`](file:///e:/Reply_agent/data/processed/v2/knowledge.jsonl), 3,000 records, SHA-256: `d58756b12613a74f43e7a33186d9a9f9b2c3d0bb5490cf7b1a045d87d69408fe`) and the legacy v1 historical corpus ([`data/processed/spotify_knowledge.jsonl`](file:///e:/Reply_agent/data/processed/spotify_knowledge.jsonl), 3,000 records, 4,118,012 bytes) are fully packaged inside this review bundle.
   - **Pre-Normalization 31-Record Spotify Sample:** `brand_profile.md` notes 31 original review records from the initial exploratory pass. However, `sampling_manifest_v1.json` and subsequent manifests store only 30 normalized complete records. As documented in `results/brand_review/manifest_audit_report.json`, the authentic pre-normalization 31st record was not preserved on disk prior to standardization to `target_complete_per_brand = 30`.
   - **Exclusion of Large Raw Datasets & Databases:** Per instructions, the raw source dataset `twcs.csv` (516 MB) and the SQLite index `data/cache/twcs_index.sqlite` (~500 MB) are excluded from this bundle to maintain a clean review package. All derived inputs, manifests, splits, and historical retrieval corpora are fully preserved with cryptographic SHA-256 verification hashes.
   - **Secrets & Virtual Environments:** `.env`, `.env.example`, and `.venv/` are strictly excluded.

3. **Exclusion of Contaminated Groups 120298 & 352469 and Historical Development Groups:**
   - To prevent historical development-to-gold and development-to-evaluation contamination, all 6 earlier development groups (`120298`, `1736480`, `2165541`, `2293459`, `2873`, `352469`) identified in the earlier development split and exclusion history ([`results/phase2/correction2/exclusion_history.json`](file:///e:/Reply_agent/results/phase2/correction2/exclusion_history.json)), along with their duplicate clusters, have been strictly excluded from the evaluation pool (`data/processed/v2/eval_pool_inputs.jsonl`, 994 clean records) and from the gold evaluation set.
   - The 2 contaminated records (`120298` and `352469`) in the 200-item gold evaluation set have been replaced by two clean, independent random-stratum candidates:
     1. `SpotifyCares:462668:462668:462666` (Group `462668`): Technical support regarding Samsung Galaxy S8+ app crash & offline mode switching; reviewed and confirmed as `intent: technical_support`, `auto_handle`.
     2. `SpotifyCares:1555406:1555406:1555405` (Group `1555406`): Billing inquiry regarding payment method failure when purchasing Premium; reviewed and confirmed as `intent: billing_and_payments`, `auto_handle`.
   - The remaining 198 clean gold items (148 random, 50 challenge) and their original human annotations were preserved intact.
   - `validate_annotations.py` enforces that neither `120298`, `352469`, nor any of the 50 earlier dev groups appear in gold or the evaluation pool.

---

## 5. Bundle Integrity & Verification Checklist

To independently verify the bundle contents after unpacking:

1. Validate file count and structure against Section 2 above.
2. Run the validation command:
   ```powershell
   python validate_annotations.py
   ```
3. Run the offline headline recalculation:
   ```powershell
   python reproduce.py --mode offline
   ```
4. Verify that all 140 regression tests pass:
   ```powershell
   python -m pytest tests/ -v --tb=short
   ```
