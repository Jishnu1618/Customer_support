# Project Decision Log: Spotify Customer Support Reply Agent

**Project:** `@SpotifyCares` Support Automation & Evaluation Pipeline  
**Version:** 1.0 (Frozen Specification)  
**Date:** September 15, 2026  

---

## 1. Architectural & Methodological Decisions

### Decision 1: Single-Conversation Partitioning for Zero Data Leakage
- **Context:** Multiple customer tweets often originate from the same user or support thread.
- **Decision:** Sample exactly 1 customer inquiry per conversation across all development and evaluation splits.
- **Rationale:** Prevents data leakage between training/tuning instances and held-out test evaluation.

### Decision 2: 8-Category Intent Taxonomy Freeze
- **Context:** Raw customer inquiries span diverse topics ranging from technical bugs to licensing and billing disputes.
- **Decision:** Standardize an 8-intent taxonomy (`content_availability`, `technical_support`, `account_access`, `billing_and_payments`, `subscription_and_plans`, `platform_and_regional`, `product_feedback`, `other_or_ambiguous`) and freeze it at Phase 3.
- **Rationale:** Ensures consistent, mutually exclusive classification boundaries for both human annotators and automated classifiers.

### Decision 3: Multi-Intent Precedence Tie-Breaking Hierarchy
- **Context:** Customer messages frequently combine multiple requests (e.g. login failure + billing charge complaint).
- **Decision:** Enforce a strict precedence order: Security (`account_access`) > Billing (`billing_and_payments`) > Tech Support (`technical_support`) > Subscription (`subscription_and_plans`) > Content (`content_availability`) > Platform (`platform_and_regional`) > Feedback (`product_feedback`) > Ambiguous (`other_or_ambiguous`).
- **Rationale:** Account security and financial disputes take priority over general feedback.

### Decision 4: Capability-Based Safety Routing Policy (`auto_handle` vs `escalate`)
- **Context:** The agent must never attempt backend database mutations or unverified financial actions.
- **Decision:** Route to `escalate` (`must_escalate = True`) whenever an inquiry involves password resets, hacked accounts, Facebook SSO deletion recovery, financial/billing disputes, or unresolved ambiguity.
- **Rationale:** Ensures 100% escalation recall on sensitive issues to protect user privacy and security.

### Decision 5: Feature-Based Challenge Set Sampling (50 Records)
- **Context:** Standard random sampling can under-represent rare or complex failure modes.
- **Decision:** Select 50 challenge messages based on objective text features (rare topics, high ambiguity, mixed requests, multi-turn failures, sensitive security) prior to observing model outputs.
- **Rationale:** Tests agent robustness against edge cases without data leakage.

### Decision 6: Composite Provenance Schema (`example_id`)
- **Context:** Need unambiguous tracking from raw dataset rows to final prediction outputs.
- **Decision:** Use `SpotifyCares:<group_id>:<cust_tweet_id>:<brand_reply_id>` as the composite primary key.
- **Rationale:** Guarantees 1-to-1 join integrity across all processing scripts and prediction logs.

### Decision 7: Standardized System Interface & Schema Across All Models
- **Context:** Baseline 0, Baseline 1, and Main Agent Pipeline require comparative evaluation.
- **Decision:** Enforce `BaseReplyAgent` abstract class requiring standard output fields (`example_id`, `system_id`, `predicted_intent`, `predicted_must_escalate`, `predicted_reply`, `predicted_reason`, `retrieved_source_ids`, `runtime_ms`).
- **Rationale:** Enables direct, automated 1-to-1 join validation across all systems.

### Decision 8: Sublinear TF-IDF Retriever Indexing Historical Problem Text Only
- **Context:** Historical brand replies can contain irrelevant Twitter handles or boilerplate URLs.
- **Decision:** Fit the TF-IDF vectorizer exclusively on historical customer inquiry text (`customer_text`) in `spotify_knowledge.jsonl`.
- **Rationale:** Maximizes retrieval relevance by matching query problem features to historical problem descriptions.

### Decision 9: 6-Stage Modular Pipeline Architecture (`src/pipeline.py`)
- **Context:** Monolithic agents make error tracing and safety audits difficult.
- **Decision:** Implement 6 discrete stages (`classify`, `retrieve`, `draft`, `validate`, `route`, `log`).
- **Rationale:** Isolates risk signal detection from drafting and validation, ensuring policy compliance before output generation.

### Decision 10: Frozen System Configuration Manifest (`frozen_config.json`)
- **Context:** Evaluation runs must be reproducible and immutable.
- **Decision:** Generate `results/phase5/frozen_config.json` containing knowledge corpus SHA-256 (`cd297fcfa...`), git commit hash, taxonomy version, and package requirements prior to final test execution.
- **Rationale:** Locks all experimental variables before executing final test evaluation.

### Decision 11: Blinded LLM Judge Evaluation & Human Validation Review Task
- **Context:** Automated judge ratings require empirical validation against independent human ratings, avoiding manufactured or synthetic agreement scores.
- **Decision:** Prepare an independent, blinded review task across 30 random message clusters (90 system replies) with empty rating columns (`results/phase6/reply_human_review_task.xlsx` and `human_ratings.csv`). Decouple historical synthetic development placeholders into explicit test fixtures (`tests/fixtures/synthetic_ratings_fixture.csv`).
- **Rationale:** Prevents synthetic placeholder scores from masquerading as human agreement; reports inter-rater agreement honestly as "Not yet measured" until independent human review is completed and signed.

### Decision 12: Separation of Post-Test Improvement Proposals
- **Context:** Ideas for model fine-tuning or reranking must not pollute frozen test results.
- **Decision:** Present post-test improvement ideas strictly in a separate roadmap section of `final_report.md`.
- **Rationale:** Preserves scientific integrity of the frozen headline evaluation experiment.

### Decision 13: Grounded Historical Evidence Display & Stable Review IDs in Human Review
- **Context:** Human annotators cannot assess grounding without inspecting the exact evidence seen by the model, and row-position-based joining of ratings is fragile.
- **Decision:** Embed the actual historical customer inquiry and brand-reply text for each retrieved evidence case (or explicitly state that no evidence was used), assign permanent `review_id` keys (`REV-001` to `REV-090`), and isolate the system identity mapping in a separate file (`results/phase6/system_identity_mapping.csv`).
- **Rationale:** Empowers human annotators with full factual context, prevents row-order misalignment during imports, and guarantees rigorous double-blind evaluation.

---

## 2. Explicit Citations & Acknowledgments

### 2.1 Primary Dataset Citation
- **Dataset:** Twitter Customer Support (TWCS) Dataset.
- **Corpus Subset:** English customer support conversations directed to `@SpotifyCares`.
- **Processed Files:** `data/processed/v2/spotify_knowledge.jsonl` (3,000 unique historical exchanges), `dev_gold.jsonl` (50 dev records), `golden_eval.jsonl` (200 eval records).

### 2.2 Third-Party Libraries & Dependencies
- `scikit-learn`: Used for sublinear TF-IDF vectorization (`TfidfVectorizer`) and cosine similarity calculations (`cosine_similarity`).
- `pandas` & `numpy`: Used for tabular data manipulation, matrix joins, and dataset profiling.
- `pyyaml`: Used for parsing and dumping frozen YAML taxonomy definitions (`intents.yaml`).
- `pytest`: Used for test suite execution (140 automated unit and regression tests).
- `openpyxl`: Used for Excel workbook generation and human annotation review auditing.

### 2.3 Tools & Development Environment
- `agy` CLI & `antigravity-ide`: Environment tools used for workspace management, command execution, and artifact building.
- `python` 3.13: Primary runtime environment.

### 2.4 AI Assistance Acknowledgment
- **AI Assistant:** Google DeepMind Antigravity AI pair programming agent (`Antigravity`).
- **Role:** Assisted in pair-programming pipeline modules, writing unit tests, executing assertion scripts, and formatting technical reports based strictly on empirical execution data.
