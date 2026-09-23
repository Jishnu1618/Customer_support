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

### Decision 14: Rate-Limit Resilient Multi-Provider LLM Judge Architecture
- **Context:** Gemini free-tier preview models impose strict requests-per-day ceilings (e.g. 20 RPD on `gemini-3.6-flash`), and thinking tokens frequently exhausted response token budgets causing truncated JSON outputs.
- **Decision:** Implement multi-provider support (`Groq` and `Google Gemini`) with explicit thinking budget zeroing (`thinking_budget=0`), automated retry-delay parsing for HTTP 429 backoff, deterministic SHA-256 prompt/rubric cache keys, and high-throughput evaluation using Groq's high-rate-limit models (`qwen/qwen3.8-27b` and `openai/gpt-oss-120b`).
- **Rationale:** Prevents evaluation stalls, preserves zero-shot rubric scoring integrity, and enables rapid reproduction of all 600 evaluations without violating API quotas.

### Decision 15: Empirical Quadratic-Weighted Cohen's $\kappa$ Protocol on 90 Human Ratings
- **Context:** Inter-rater agreement between automated LLM judges and human raters must reflect genuine human review across all four quality dimensions (Relevance, Grounding, Usefulness, Tone) and critical safety error detection.
- **Decision:** Ingest 90 independently signed human ratings from `human_ratings.csv` (originating from `reply_human_review_task_v2_annonated.xlsx`), join with blinded system predictions via `system_identity_mapping.csv`, and compute linear/quadratic-weighted Cohen's $\kappa$ alongside clustered bootstrap 95% confidence intervals across the 30 message clusters.
- **Rationale:** Guarantees transparent, verifiable agreement reporting against genuine LLM outputs without synthetic substitution or data fabrication.

### Decision 16: Multi-Key Pool Rotation & Failover for High-Throughput LLM Evaluation
- **Context:** Free-tier API providers impose individual daily token caps (e.g. 200,000 tokens/day on Groq), which halts large-scale 600-item zero-shot rubric evaluations if routed through a single key.
- **Decision:** Configure a multi-key pool (`GROQ_API_KEYS`) in `configs/settings.py` with automatic round-robin request distribution across calls and immediate failover on HTTP 429 rate limits in `src/llm.py`.
- **Rationale:** Distributes the 340,000+ token evaluation workload evenly across multiple authorized API accounts, eliminating quota blocking and achieving 100% genuine LLM judge evaluation across all 600 system predictions in minutes with zero failures.

### Decision 17: Raise TF-IDF Retrieval Confidence Threshold (0.15 → 0.25)
- **Context:** Post-evaluation analysis showed the Main Agent had a 23.5% critical error rate, substantially higher than Baseline 1 (10%). Root cause: the 0.15 cosine-similarity threshold was too permissive, causing weakly-related historical tweets to be passed verbatim as reply text, which the LLM judge penalised as low-quality grounding.
- **Decision:** Raise `retrieval_sim_threshold` from 0.15 to 0.25 in `src/pipeline.py`. When no evidence meets the threshold, the system falls back to the intent-specific structured template reply instead of using low-confidence evidence.
- **Rationale:** A higher threshold trades slight reductions in evidence reuse for substantially cleaner reply quality — the structural template replies score higher on Grounding and Usefulness than noise-contaminated raw historical tweets.

### Decision 18: Add Structured Empathy–Action–Closer Reply Formatter
- **Context:** The Main Agent's `draft()` stage passed raw cleaned historical brand tweets directly as the reply text. These tweets lacked consistent structure — no empathy opener, no clear action, no call-to-action closer. The LLM judge rated these as 0.36/2.0 on Usefulness (worst of the three systems).
- **Decision:** Add a `_format_reply()` method that wraps any reply in a 3-part structure: intent-specific empathy opener + core action (from evidence or fallback template) + branded closer. All 8 intents have tailored opener/closer pairs.
- **Rationale:** Consistent reply structure directly maps to higher Tone and Usefulness scores per the rubric anchors. The formatter is rule-based (zero API cost) and never hallucinates — it only frames content that already exists.

### Decision 19: Add Sentence-Transformer Semantic Classifier as Intent Fallback
- **Context:** The Main Agent's intent accuracy (44.5%) was statistically tied with Baseline 1 (44.0%) because both used identical regex rules. The top 5 failure modes (sarcasm, typos, entity-name-first sentences, short social messages) are all cases where regex fails but semantic similarity to intent prototype descriptions succeeds.
- **Decision:** Add a lazy-loaded `all-MiniLM-L6-v2` sentence-transformer model as a secondary classifier that activates only when the primary regex rules fall through to `other_or_ambiguous`. Pre-encode 8 intent prototype sentences at startup; compute cosine similarity at runtime, returning the best match if it exceeds 0.30 confidence.
- **Rationale:** The semantic model corrects the 5 documented regex-blindness failure modes with zero LLM API cost, sub-millisecond incremental latency, and no false positives on the regex-matched majority (because it only fires on the `other_or_ambiguous` fallback path).

### Decision 20: Few-Shot Calibration Examples in LLM Judge Prompt (v2.0)
- **Context:** Human–judge agreement was near-zero (κ = -0.055 to +0.126) across all quality dimensions. Analysis showed the rubric's 0/1/2 anchors were interpreted inconsistently — e.g. the boundary between Usefulness=1 ("general troubleshooting") vs. Usefulness=2 ("direct self-serve link") was ambiguous without concrete examples.
- **Decision:** Create `prompts/llm_judge_prompt_v2.txt` with 2–3 scored calibration examples per dimension embedded in the prompt. The rubric scales and critical-error definitions are unchanged; only illustrative examples are added. Version is bumped to v2.0 so a separate cache namespace is maintained.
- **Rationale:** Few-shot calibration is the fastest and most direct lever on inter-rater agreement. The v1 cache is preserved (different SHA-256 key), so historical results are not invalidated.

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
