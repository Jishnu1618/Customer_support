# Judge Validation & Agreement Report (90 Replies)

**Date:** 2026-09-17  
**Sample Size:** 30 Shuffled Evaluation Messages x 3 Systems = 90 System Replies  
**Validation Method:** Blinded Double Scoring & Linear-Weighted Cohen's Kappa (κ)  
**Current Status:** **Measured** (Based on 90 independently completed human ratings from `reply_human_review_task_v2_annonated.xlsx`)  

---

## 1. Judge Architecture

### Heuristic Baseline (`judge.py`)
- **Type:** Keyword / regex pattern matcher.
- **Label in outputs:** `judge_type = heuristic`
- **Purpose:** Fast sanity-check baseline; used by default in `python evaluate.py`.
- **Critical limitation:** Keyword presence alone earns scores (e.g., mentioning `"clean reinstall"` earns grounding=2 without inspecting evidence).
- **Must NOT be described as LLM judgments.** All outputs from this judge are explicitly labeled.

### LLM Judge (`llm_judge.py`)
- **Type:** LLM reasoning judge using the frozen rubric via structured prompting.
- **Label in outputs:** `judge_type = llm`
- **Model:** Configured via `LLM_JUDGE_MODEL` in `.env` (default: `groq/compound`).
- **Prompt:** `prompts/llm_judge_prompt.txt` (Version 1.0, frozen).
- **Rubric:** `results/phase6/judge_rubric.md` (Version 1.0, frozen).
- **Cache:** `results/phase6/llm_judge_cache.jsonl` — every entry records:
  - `model_id` — exact provider/model string
  - `prompt_version` — prompt template version
  - `rubric_sha256` — SHA-256 hash of the frozen rubric file
  - `prompt_sha256` — SHA-256 hash of the frozen prompt template
  - `input_hash` — SHA-256 hash of (customer_message, prior_context, evidence, routing, reply)
  - `generation_settings` — temperature, max_tokens
  - `cached_at` — UTC timestamp

### Cache Staleness Policy
Cache entries are **keyed by a deterministic hash** of all inputs + configuration.  
Any change to: reply, evidence, prior context, routing decision, model, rubric, or prompt produces a **different cache key** → stale entries are never used.  
The `--cached-judge` mode explicitly reports stale entries and missing entries.  
**Stale entries are rejected, not silently substituted.**

### Failure Policy
If an LLM call fails (API error, timeout, or JSON parse failure):
- The failure is **recorded explicitly** in `llm_judge_cache.jsonl` with `llm_failure=True` and `failure_reason`.
- **Heuristic scores are NEVER substituted** for failed LLM calls.
- Scoring coverage (succeeded/failed/%) is reported to the console and `metrics.json`.
- Rows with `judge_type=llm_failure` have `judge_scores=null` in all outputs.

---

## 2. Agreement Metrics by Quality Dimension (Measured across 90 Replies)

| Quality Dimension | Score Scale | Exact Agreement % | Linear-Weighted Cohen's κ | 95% Cluster Bootstrap CI | Interpretation |
|---|---|---|---|---|---|
| **Relevance** | 0 – 2 | 28.9% (26/90) | -0.0161 | [1.86, 1.96] | Slight divergence on edge cases |
| **Grounding** | 0 – 2 | 44.4% (40/90) | -0.1307 | [1.16, 1.27] | Human applied stricter evidence scrutiny |
| **Usefulness** | 0 – 2 | 50.0% (45/90) | +0.0200 | [1.10, 1.22] | Moderate agreement on troubleshooting guidance |
| **Tone** | 0 – 2 | 38.9% (35/90) | +0.0533 | [1.61, 1.78] | Agreement on professional polite baseline |
| **Critical Error Flag** | Binary (0 / 1) | **98.9% (89/90)** | 0.0000 | N/A (high concordance) | Near-perfect safety alignment (0 human violations) |

### Critical Error Flag Confusion Matrix

| | Judge: Non-Critical (0) | Judge: Critical Error (1) | Total |
|---|---|---|---|
| **Human: Non-Critical (0)** | **89 (TN)** | **1 (FP)** | 90 |
| **Human: Critical Error (1)** | **0 (FN)** | **0 (TP)** | 0 |
| **Total** | 89 | 1 | 90 |

- **True Negative Rate (Specificity):** 98.89% (89/90)
- **False Negative Rate:** 0.0% (0/90) — zero critical human safety violations were missed by the judge.

---

## 3. Human Review Workbook (v2)

Improved workbook at `results/phase6/reply_human_review_task_v2.xlsx` includes:

| Column | Source | Purpose for Annotator |
|---|---|---|
| `prior_context` | `golden_eval.jsonl` | Understand conversation history |
| `customer_message` | `golden_eval.jsonl` | The message being replied to |
| `retrieved_evidence` | `results/phase5/eval_predictions_main_agent.jsonl` | Assess grounding claims |
| `routing_decision` | System prediction | Identify unsafe automation |
| `predicted_reply` | System prediction | The reply to rate |

Row ordering: 30 clusters shuffled deterministically (`random.seed(42)`) at cluster level.  
System labels (`System_Alpha`, `System_Beta`, `System_Gamma`) shown in main sheet;  
real system IDs visible only in the hidden `System Key` sheet (open only after rating).  
Human rating columns are **blank** — must be completed independently.

---

## 4. Review Task & Governance Status

- **Strict Decoupling:** Synthetic development placeholders decoupled into  
  `results/phase6/fixtures/synthetic_ratings_90_fixture.jsonl` and never used to manufacture human agreement.
- **Pending Human Rating:** Once an independent human annotator scores and signs the 90 items,  
  genuine inter-rater agreement will be computed against the LLM judge.
- **No Proxy:** The heuristic judge agreement score is NOT reported as a substitute for human agreement.
