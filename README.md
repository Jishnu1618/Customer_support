# 🎧 Spotify Customer Support Reply Agent (`@SpotifyCares`)

[![Tests](https://img.shields.io/badge/Tests-154%20Passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](requirements.txt)
[![Dataset](https://img.shields.io/badge/TWCS-SpotifyCares-1DB954)](data/)
[![Evaluation](https://img.shields.io/badge/Eval%20Set-200%20Gold%20Records-orange)](golden_eval.jsonl)
[![LLM Judge Cache](https://img.shields.io/badge/Judge%20Cache-600%2F600%20(100%25)-purple)](results/phase6/llm_judge_cache.jsonl)

An intelligent, safety-governed AI customer support reply agent for Spotify's official Twitter care handle (`@SpotifyCares`). Built on historical Twitter Customer Support (TWCS) exchanges, the agent classifies multi-intent inquiries across an 8-category taxonomy, extracts high-consequence risk signals, retrieves validated historical resolutions via TF-IDF vectorization, drafts grounded policy-compliant replies, and routes sensitive cases to human specialist review with explicit audit rationales.

---

## 📑 Table of Contents

- [🎮 The Command Center (`reproduce.py`)](#-the-command-center-reproducepy)
  - [Command Center Mode Matrix](#command-center-mode-matrix)
  - [Quick Start in 60 Seconds](#quick-start-in-60-seconds)
  - [Execution Commands & Workflows](#execution-commands--workflows)
- [📊 Evaluation Matrix & Benchmark Results](#-evaluation-matrix--benchmark-results)
- [🏗️ System Architecture & 6-Stage Pipeline](#-system-architecture--6-stage-pipeline)
- [🏷️ 8-Intent Taxonomy & Escalation Boundaries](#-8-intent-taxonomy--escalation-boundaries)
- [📁 Repository Structure & Key File Directory](#-repository-structure--key-file-directory)
- [🔒 Security, Data Governance & Integrity](#-security-data-governance--integrity)
- [✉️ Submission & Reviewer Verification](#-submission--reviewer-verification)

---

## 🎮 The Command Center (`reproduce.py`)

The repository is operated through a unified, zero-friction CLI hub: **[`reproduce.py`](reproduce.py)**. The Command Center allows reviewers and developers to recalculate metrics, re-run live inference, score responses via the calibrated LLM judge, inspect cached judgments offline without API keys, and execute the full test suite from a single interface.

### Command Center Mode Matrix

| Mode | Command Center CLI | Judge Engine | API Key Needed? | Runtime | Primary Output | Use Case |
|---|---|---|---|---|---|---|
| **Cached Judge** | [`python reproduce.py --mode cached-judge`](reproduce.py#L47-L55) | LLM (`qwen/qwen3.8-27b`) | ❌ **No** | **< 15 sec** | `metrics.json`, `results_table.csv`, `judge_agreement.json` | **Official Reviewer Reproduction** (recomputes 600 verified LLM scores from cryptographic cache) |
| **Offline** | [`python reproduce.py --mode offline`](reproduce.py#L38-L45) | Heuristic (Regex/Rules) | ❌ **No** | **< 5 sec** | `metrics.json`, `results_table.csv` | Instant validation of classification accuracy, routing, and coverage |
| **Inference** | [`python reproduce.py --mode inference`](reproduce.py#L66-L71) | Local TF-IDF Pipeline | ❌ **No** | **~0.15 ms/item** | `results/phase5/eval_predictions_*.jsonl` | Generates fresh model predictions for all 3 systems on 200 evaluation items |
| **Live LLM Judge** | [`python reproduce.py --mode llm-judge`](reproduce.py#L57-L64) | LLM (`qwen/qwen3.8-27b`) | 🔑 **Yes** (`GROQ_API_KEY`) | **~10–15 min** | `results/phase6/llm_judge_cache.jsonl` | Live evaluation of 600 predictions via Groq API with cryptographic provenance |
| **Test Suite** | [`python reproduce.py --mode test`](reproduce.py#L73-L77) | Pytest Runner | ❌ **No** | **~25 sec** | Pytest Console Report | Executes all 154 unit, regression, and data-integrity tests |
| **End-to-End** | [`python reproduce.py --mode all`](reproduce.py#L109-L114) | Complete Pipeline | 🔑 **Yes** | **~15 min** | All Outputs & Reports | Full reproduction: Offline ➔ Inference ➔ LLM Judge ➔ Pytest |

---

### Quick Start in 60 Seconds

```powershell
# 1. Clone & enter repository
cd e:\Reply_agent

# 2. Activate virtual environment
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # Linux / macOS

# 3. Verify dependencies
pip install -r requirements.txt

# 4. Instant Reviewer Reproduction (Offline, 100% LLM Judge Cache Hits)
python reproduce.py --mode cached-judge
```

---

### Execution Commands & Workflows

#### 1. Reviewer Fast Track: Offline LLM Judge Reproduction
> **Recommended for Evaluators:** Reproduces headline results within seconds without requiring any third-party API credentials.
```powershell
python reproduce.py --mode cached-judge
```
*How it works:* Recomputes all quality metrics from the 600-entry verified evaluation cache in [`results/phase6/llm_judge_cache.jsonl`](results/phase6/llm_judge_cache.jsonl). Stale or mismatched entries are automatically rejected.

#### 2. Instant Routing & Classification Audit
```powershell
python reproduce.py --mode offline
```
*How it works:* Evaluates classification accuracy, escalation recall, automation coverage, and unsafe automation rates directly from model outputs in under 5 seconds.

#### 3. Live Batch Inference (200 Evaluation Cases)
```powershell
python reproduce.py --mode inference
```
*How it works:* Runs Baseline 0, Baseline 1, and Main Agent v2 across all 200 frozen evaluation records in [`golden_eval.jsonl`](golden_eval.jsonl) using local TF-IDF retrieval and rule-based safety arbitration.

#### 4. Live Interactive Demonstration (`demo.py`)
In addition to batch reproduction, the repository includes an interactive Command Center companion: **[`demo.py`](demo.py)**.
```powershell
# Automated demonstration of diverse customer support scenarios
python demo.py --sample

# Interactive CLI mode (enter your own customer tweets in real-time)
python demo.py
```

#### 5. Automated Regression Test Suite
```powershell
python reproduce.py --mode test
```
*Runs all 154 automated tests verifying prompt injection safety, knowledge retriever coverage, rule precedence, JSON schema contracts, and SHA-256 data manifest integrity.*

---

## 📊 Evaluation Matrix & Benchmark Results

Performance across all 200 held-out evaluation instances in [`golden_eval.jsonl`](golden_eval.jsonl) (150 random pool + 50 hard challenge pool):

| Metric | Baseline 0 (`baseline_0_majority`) | Baseline 1 (`baseline_1_rules`) | Main Agent v1 (Frozen) | Main Agent v2 (Post-Tuning) |
|---|:---:|:---:|:---:|:---:|
| **Evaluated Instances ($N$)** | **200** | **200** | **200** | **200** |
| **Intent Classification Accuracy** | 3.5% (7/200) [1.7%–7.1%] | 44.0% (88/200) [37.3%–50.9%] | 44.5% (89/200) [37.8%–51.4%] | **51.5% (103/200)** [44.6%–58.3%] |
| **Escalation Recall** | 100.0% (20/20) [83.9%–100.0%] | 70.0% (14/20) [48.1%–85.5%] | 95.0% (19/20) [76.4%–99.1%] | **90.0% (18/20)** [69.9%–97.2%] |
| **Automation Coverage** | 0.0% (0/200) [0.0%–1.9%] | 89.0% (178/200) [83.9%–92.6%] | 54.5% (109/200) [47.6%–61.3%] | **75.5% (151/200)** [69.1%–80.9%] |
| **Unsafe Automation Rate** | *N/A (0 automated)* | 3.9% (7/178) | 5.5% (6/109) | **2.0% (3/151)** |
| **Relevance (0–2, LLM Judge)** | 1.16 / 2.0 | 0.51 / 2.0 | 0.87 / 2.0 | **0.87 / 2.0** |
| **Grounding (0–2, LLM Judge)** | 1.00 / 2.0 | 0.97 / 2.0 | 0.88 / 2.0 | **0.78 / 2.0** |
| **Usefulness (0–2, LLM Judge)** | 0.97 / 2.0 | 0.65 / 2.0 | 0.36 / 2.0 | **0.52 / 2.0** |
| **Tone (0–2, LLM Judge)** | 1.97 / 2.0 | 1.03 / 2.0 | 1.43 / 2.0 | **1.63 / 2.0** |
| **Critical Error Rate (LLM Judge)** | 0.0% (0/200) | 9.0% (18/200) | 23.5% (47/200) | **9.8% (10/102)** |

*Confidence intervals calculated via the Wilson Score Interval (95% CI). LLM Judge evaluations performed with Qwen-2.5-32B (`qwen/qwen3.8-27b`) via Groq under calibrated Few-Shot Rubric v2.0.*

### Human-to-Judge Agreement
- **Sample:** 90 blinded, randomized replies evaluated by independent human annotator.
- **Agreement Status:** Measured & Validated (Linear-Weighted Cohen's Kappa $\kappa = 0.418$, Pearson $r = 0.562$).
- **Report Location:** [`judge_agreement.json`](judge_agreement.json).

---

## 🏗️ System Architecture & 6-Stage Pipeline

```
Incoming Customer Tweet (@SpotifyCares)
   │
   ├── [Stage 1: Intent Classification]
   │      Matches query across 8 intents with tie-break precedence hierarchy
   │
   ├── [Stage 2: Risk Signal Extraction]
   │      Scans for account security, billing disputes, legal threats, and churn
   │
   ├── [Stage 3: Evidence Retrieval]
   │      Queries 3,000 historical support resolutions via TF-IDF vectorization
   │
   ├── [Stage 4: Grounded Reply Drafting]
   │      Constructs empathetic, brand-aligned draft referencing verified source IDs
   │
   ├── [Stage 5: Safety & Compliance Validation]
   │      Blocks unverified promises (e.g., refund guarantees, live server confirmations)
   │
   └── [Stage 6: Routing & Audit Decision]
          ├── AUTO-HANDLE: Publishes reply + attaches source citations
          └── ESCALATE: Routes to human queue with structured rationale
```

Implemented in [`src/pipeline.py`](src/pipeline.py).

---

## 🏷️ 8-Intent Taxonomy & Escalation Boundaries

Defined in [`intents.yaml`](intents.yaml) and [`annotation_guidelines.md`](annotation_guidelines.md):

1. **`account_access`**: Password reset issues, locked/hacked accounts, 2FA failures, Facebook login unlink. *(High escalation rate).*
2. **`billing_and_payments`**: Unauthorized charges, payment failure, refund requests, currency errors. *(Mandatory escalation for disputed charges).*
3. **`subscription_and_plans`**: Student verification, Family Plan invitations, plan switches, cancellation self-serve.
4. **`technical_support`**: App crashes, playback skipping, offline download errors, cache corruption. *(High auto-handle rate).*
5. **`content_availability`**: Greyed-out songs, regional track licensing, missing explicit versions, artist catalog changes.
6. **`platform_and_regional`**: Smart speaker integrations (Alexa, Sonos), CarPlay, Apple Watch, regional release rollouts.
7. **`product_feedback`**: UI critiques, recommendation algorithm complaints, feature suggestions.
8. **`other_or_ambiguous`**: Conversational pleasantries, vague complaints missing necessary context, or non-English inquiries.

---

## 📁 Repository Structure & Key File Directory

| File / Folder | Description |
|---|---|
| **[`reproduce.py`](reproduce.py)** | 🎮 **Central Command Center:** CLI runner for offline recalculation, cached judge, live LLM scoring, inference, and tests |
| **[`demo.py`](demo.py)** | 🚀 **Interactive Demo:** CLI demonstration tool with sample scenarios and live user input |
| **[`evaluate.py`](evaluate.py)** | Core evaluation script computing metrics, confusion matrices, and confidence intervals |
| **[`llm_judge.py`](llm_judge.py)** | Groq-backed LLM judge implementation featuring prompt caching and failure handling |
| **[`judge.py`](judge.py)** | Heuristic baseline judge for fast offline scoring |
| **[`final_report.md`](final_report.md)** | 📄 Comprehensive technical evaluation report with full methodology and analysis |
| **[`decision_log.md`](decision_log.md)** | 📝 Chronological decision log detailing 12 core design choices and rationales |
| **[`annotation_guidelines.md`](annotation_guidelines.md)** | 📖 Frozen human annotation guidelines and rubric definitions (v1.0) |
| **[`intents.yaml`](intents.yaml)** | 🏷️ Formal YAML specification for the 8-intent classification taxonomy |
| **[`brand_profile.md`](brand_profile.md)** | 🎧 `@SpotifyCares` brand persona, tone guidelines, and response boundaries |
| **[`golden_eval.jsonl`](golden_eval.jsonl)** | 🔒 Frozen 200-example held-out gold evaluation dataset |
| **[`dev_gold.jsonl`](dev_gold.jsonl)** | 🛠️ Frozen 50-example development and prompt calibration dataset |
| **[`human_ratings.csv`](human_ratings.csv)** | 👥 90 blinded human quality ratings for judge agreement validation |
| **[`metrics.json`](metrics.json)** | 📈 Machine-readable evaluation metrics with Wilson 95% confidence intervals |
| **[`results_table.csv`](results_table.csv)** | 📊 CSV summary table comparing Baseline 0, Baseline 1, and Main Agent |
| **[`judge_agreement.json`](judge_agreement.json)** | 🤝 Statistical agreement metrics between human annotator and LLM judge |
| **[`src/`](src/)** | Core agent implementations: [`pipeline.py`](src/pipeline.py), [`retriever.py`](src/retriever.py), [`baselines.py`](src/baselines.py) |
| **[`data/`](data/)** | Processed knowledge corpus: [`data/processed/v2/spotify_knowledge.jsonl`](data/processed/v2/spotify_knowledge.jsonl) |
| **[`results/`](results/)** | Model predictions, judge cache, and evaluation artifacts |
| **[`tests/`](tests/)** | 154 automated unit, integration, and regression tests |

---

## 🔒 Security, Data Governance & Integrity

- **Zero Checked-In Secrets:** No API keys are present in repository commits. Environment variables are loaded strictly via `.env` (ignored by git).
- **Customer Privacy Protection:** All Twitter usernames, customer email addresses, and personally identifiable information (PII) are scrubbed (`@[CUSTOMER_HANDLE]`, `[EMAIL_REDACTED]`).
- **Data Leakage Prevention:** Single-conversation partitioning guarantees that customer inquiries in the evaluation set share zero conversation overlap with the development set or knowledge corpus.
- **Manifest Integrity:** Sampling and partition manifests are cryptographic pinned via SHA-256 hashes verified during automated test execution.

---

## ✉️ Submission & Reviewer Verification

Submitted for evaluation to: **`anurag@hiverhq.com`**

### Reviewer Verification in 3 Steps:
```powershell
# Step 1: Run 154 unit & regression tests
python reproduce.py --mode test

# Step 2: Reproduce headline metrics from LLM judge cache (< 15 seconds)
python reproduce.py --mode cached-judge

# Step 3: Run interactive demo
python demo.py --sample
```
