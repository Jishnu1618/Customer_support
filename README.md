# Reply Agent 🤖 (Phase 8 Final Package)

An intelligent, safety-governed customer support reply agent for Spotify Twitter support (`@SpotifyCares`). It classifies customer intents, extracts risk signals, queries historical support exchanges via TF-IDF vectorization, validates draft compliance, and routes sensitive/complex inquiries to human specialist review.

---

## 🚀 Quick Start & Reproducibility (Under 15 Minutes)

### 1. Environment Setup (Fresh Environment)
**Prerequisites:** Python 3.10+ installed.  
No API key is required for offline metrics or inference reproduction.  
An API key (`GROQ_API_KEY`) is required only for live LLM judge scoring.

```bash
# Navigate to the repository root
cd e:\Reply_agent

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux/macOS

# Install requirements
pip install -r requirements.txt
```

---

## ⚡ Reproduction Commands

### Command A: Fast Offline Recalculation of Classification & Routing Metrics
`< 5 seconds, no API key required`

Recalculates classification accuracy, escalation recall, and automation coverage from saved predictions.
**Reply-quality scores use the heuristic judge (keyword/regex-based). They are labeled `judge_type=heuristic` in all outputs and must NOT be interpreted as LLM judgments.**

```powershell
python reproduce.py --mode offline
# OR
python evaluate.py
```

Outputs: `metrics.json`, `results_table.csv`, `judge_agreement.json`

---

### Command B: Offline LLM Judge Metrics (No API Key Required)
`< 1 minute, no API key required — designed for reviewers`

Recomputes all metrics from **saved LLM judgments** without making any API calls.
This recomputes metrics from `results/phase6/llm_judge_cache.jsonl`.
Stale cache entries (when replies, evidence, or judge configuration have changed) are detected and rejected — they are never silently used.

```powershell
python reproduce.py --mode cached-judge
# OR
python evaluate.py --cached-judge
```

> **For reviewers:** This command lets you reproduce LLM-graded headline results within 15 minutes  
> without API credentials. The cache file records: model ID, prompt version, rubric SHA-256,  
> input hash, and generation settings for every judgment.

Outputs: `metrics.json` (labeled `judge_mode=llm_cached`), `results_table.csv`, `judge_agreement.json`

---

### Command C: Live LLM Judge Scoring (API Key Required)
`~10–20 minutes for 600 records, requires GROQ_API_KEY in .env`

Runs the actual LLM judge (`groq/compound`) on all 600 system predictions.
Results are cached in `results/phase6/llm_judge_cache.jsonl` with full provenance:
model ID, prompt version, rubric SHA-256, input hash, and generation settings.

**Coverage is reported (succeeded/failed/%).  
Failures are recorded explicitly. Heuristic scores are NEVER silently substituted.**

```powershell
python reproduce.py --mode llm-judge
# OR
python evaluate.py --llm
```

---

### Command D: Live Model Inference (Sub-Millisecond, No API Key Required)
Runs live inference for all 3 systems on the 200 evaluation records:

```powershell
python reproduce.py --mode inference
# OR
.venv\Scripts\python.exe -m src.run_phase5_eval
```

- **Model Access:** Local Deterministic TF-IDF Retriever & Rule Reranker.
- **Measured Runtime:** ~0.145 ms per item.
- **API Cost:** $0.00.

---

### Command E: Run Full Test Suite
```powershell
python reproduce.py --mode test
# OR
.venv\Scripts\python.exe -m pytest
```

---

## 📋 Evaluation Mode Summary

| Command | Judge Type | API Key? | Time | Purpose |
|---|---|---|---|---|
| `python evaluate.py` | Heuristic (labeled) | No | < 5s | Classification/routing metrics |
| `python evaluate.py --llm` | **LLM** (live) | Yes | ~15 min | Submit quality scores |
| `python evaluate.py --cached-judge` | **LLM** (from cache) | No | < 1 min | Reviewer offline reproduction |

> **Key invariants:**
> - Heuristic and LLM scores are never mixed in the same `metrics.json`.
> - All outputs are labeled with `judge_mode` (heuristic / llm / llm_cached).
> - Human–judge agreement is computed only from independently completed human ratings.
>   Missing ratings are reported as "Not yet measured."

---

## 📁 Repository Structure & Deliverables

```
Reply_agent/
├── README.md                          # Phase 8 final documentation & reproduction guide
├── requirements.txt                  # Dependency specifications
├── intents.yaml                      # Frozen 8-intent taxonomy definitions
├── annotation_guidelines.md          # Frozen v1.0 human annotation guidelines
├── dev_gold.jsonl                    # 50 development gold label records
├── golden_eval.jsonl                 # 200 held-out evaluation gold label records
├── sampling_notes.md                 # Sampling strategy & test-retest consistency log
├── final_report.md                   # Comprehensive final evaluation report
├── report.md                         # Copy of final evaluation report
├── decision_log.md                   # 12-item decision log & explicit citations
├── reproduce.py                      # Phase 8 CLI runner (offline, inference, judge, test)
├── evaluate.py                       # Evaluation pipeline (--llm, --cached-judge, or heuristic default)
├── judge.py                          # Heuristic baseline judge (keyword/regex, labeled heuristic)
├── llm_judge.py                      # LLM judge with caching, provenance, and failure recording
├── metrics.json                      # System metrics with Wilson 95% CIs
├── results_table.csv                 # CSV comparison table across all 3 systems
├── human_ratings.csv                 # 90 blinded human validation reply ratings
├── judge_agreement.json              # Linear-weighted Cohen's Kappa & cluster CIs
├── configs/                          # Application settings & brand config
├── src/                              # Core source code modules
│   ├── baselines.py                  # Baseline 0 and Baseline 1 agent implementations
│   ├── retriever.py                  # TF-IDF historical knowledge retriever
│   ├── pipeline.py                   # 6-stage Main Agent pipeline (classify, retrieve, draft, validate, route, log)
│   ├── run_baselines.py              # Baseline execution & evaluation script
│   ├── run_phase5_dev.py             # Dev set inspection, tuning, & dev predictions
│   ├── run_phase5_eval.py            # Final freeze & 200-record evaluation runner
│   └── evaluate_phase6.py            # Phase 6 join validation & LLM Judge evaluator
├── results/                          # Output predictions & reports
│   ├── phase4/                       # Baseline predictions & report
│   ├── phase5/                       # Frozen config, tuning log, & eval predictions
│   └── phase6/                       # Blinded judge predictions, cache, agreement log
│       ├── judge_predictions_600.jsonl   # Heuristic judge scores (labeled heuristic)
│       ├── llm_judge_cache.jsonl         # LLM judge cache with full provenance
│       └── reply_human_review_task_v2.xlsx  # Improved workbook with context + evidence
└── tests/                            # 140 automated unit & regression tests
    ├── test_baselines.py             # Baseline unit tests
    ├── test_pipeline.py              # Pipeline unit tests
    └── test_phase6.py                # Phase 6 metric & kappa unit tests
```

---

## 📊 Summary Results Table (200 Evaluation Messages)

| Metric | Baseline 0 (`baseline_0_majority`) | Baseline 1 (`baseline_1_rules`) | Main Agent v1 (Frozen) | Main Agent v2 (Post-Tuning) |
|---|---|---|---|---|
| **Evaluated Messages (N)** | **200** | **200** | **200** | **200** |
| **Intent Classification Accuracy** | 3.5% (7/200) [1.7%–7.1%] | 44.0% (88/200) [37.3%–50.9%] | 44.5% (89/200) [37.8%–51.4%] | **51.5% (103/200) [44.6%–58.3%]** |
| **Escalation Recall** | 100.0% (20/20) [83.9%–100.0%] | 70.0% (14/20) [48.1%–85.5%] | 95.0% (19/20) [76.4%–99.1%] | **90.0% (18/20) [69.9%–97.2%]** |
| **Automation Coverage** | 0.0% (0/200) [0.0%–1.9%] | 89.0% (178/200) [83.9%–92.6%] | 54.5% (109/200) [47.6%–61.3%] | **75.5% (151/200) [69.1%–80.9%]** |
| **Unsafe Automation Rate** | N/A (0 automated) | 3.9% (7/178) | 5.5% (6/109) | **2.0% (3/151)** |
| **Relevance (0–2, LLM Judge)** | 1.16 / 2.0 | 0.51 / 2.0 | 0.87 / 2.0 | **0.87 / 2.0** |
| **Grounding (0–2, LLM Judge)** | 1.00 / 2.0 | 0.97 / 2.0 | 0.88 / 2.0 | **0.78 / 2.0** |
| **Usefulness (0–2, LLM Judge)** | 0.97 / 2.0 | 0.65 / 2.0 | 0.36 / 2.0 | **0.52 / 2.0** |
| **Tone (0–2, LLM Judge)** | 1.97 / 2.0 | 1.03 / 2.0 | 1.43 / 2.0 | **1.63 / 2.0** |
| **Critical Error Rate (LLM Judge)** | 0.0% (0/200) | 9.0% (18/200) | 23.5% (47/200) | **9.8% (10/102)** |

*Note: Reply quality scores are evaluated via the LLM Judge (`qwen/qwen3.8-27b`) with prompt v2.0 few-shot calibration. 95% Confidence Intervals calculated via Wilson score method.*

---

## 🔒 Security & Data Sharing Compliance
- **No Checked-In Secrets:** `.env` is ignored by `.gitignore`. `.env.example` contains only non-sensitive environment templates.
- **Redacted Data Only:** All customer Twitter handles and email addresses in processed data are redacted (`@[CUSTOMER_HANDLE]`, `[EMAIL_REDACTED]`).
- **Complete Counts:** 50 dev records, 200 eval records, 600 system predictions, 90 human validation ratings.

---

## ✉️ Submission Instructions (Manual Final Action)

To complete final submission, submit the repository link and report to `anurag@hiverhq.com`:

**Recipient:** `anurag@hiverhq.com`  
**Subject:** `[Submission] Spotify Customer Support Reply Agent - Final Evaluation & Codebase`  
**Attachment:** `final_report.md` (or `report.md`)  

*Sample Email Text:*
> Dear Anurag,
> 
> Please find submitted the final codebase, evaluation data, and technical report for the Spotify Customer Support Reply Agent project.
> 
> - **Repository Link:** `e:/Reply_agent`
> - **Final Report:** `final_report.md` / `report.md`
> - **Reproduction Command:** `python reproduce.py --mode offline` (recalculates headline results in under 5 seconds without an API key).
> 
> Sincerely,  
> Reply Agent Project Team
