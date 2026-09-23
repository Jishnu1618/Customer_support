# 🚀 Reply Agent — Complete Commands Runbook

> **Project:** Spotify Customer Support Reply Agent (`@SpotifyCares`)  
> **Repo Root:** `e:\Reply_agent`  
> **Status as of:** 2026-09-22 | Phase 8 Final  

---

## 📊 Current Status Snapshot

| Component | Status | Detail |
|---|---|---|
| **Test Suite** | ✅ **154 passed, 0 failed** | All unit + regression tests green |
| **Offline Metrics** | ✅ **Verified** | `python reproduce.py --mode offline` exits 0 |
| **Cached-Judge Metrics** | ⚠️ **Partial Cache** | 441/600 (73.5%) hits — 159 missing → need `llm-judge` run |
| **LLM Judge Cache** | ⚠️ **Needs Top-up** | Run `--mode llm-judge` with `GROQ_API_KEY` to fill gaps |
| **Golden Eval Set** | ✅ **200 records** | `golden_eval.jsonl` (150 random + 50 challenge) |
| **Human Ratings** | ✅ **90 blinded ratings** | `human_ratings.csv` + `judge_agreement.json` |
| **Final Report** | ✅ **Complete** | `final_report.md` (212 lines, all 6 required sections) |
| **Decision Log** | ✅ **Complete** | `decision_log.md` (12 decisions) |
| **Annotation Guidelines** | ✅ **Frozen v1.0** | `annotation_guidelines.md` |

### Current Evaluation Numbers (LLM-Cached Judge, 441/600 hits)

| Metric | Baseline 0 | Baseline 1 | **Main Agent** |
|---|---|---|---|
| Intent Accuracy | 3.5% | 44.0% | **44.5%** |
| Escalation Recall | 100.0% | 70.0% | **95.0%** |
| Automation Coverage | 0.0% | 89.0% | **54.5%** |
| Unsafe Automation Rate | N/A | 3.9% | **5.5%** |
| Critical Error Rate (LLM) | 0.0% | 10.0% | **23.5%** |
| Relevance (0–2) | 1.25 | 0.59 | 0.87 |
| Grounding (0–2) | 1.80 | 1.38 | 0.88 |
| Usefulness (0–2) | 0.89 | 0.49 | 0.36 |
| Tone (0–2) | 1.98 | 1.04 | 1.43 |

> **Known Issue:** Main Agent v1 has a high critical error rate (23.5%) and low usefulness score.  
> v2 improvements (raised retrieval threshold, reply formatter, semantic intent fallback) are implemented  
> in `src/pipeline.py` and require a fresh `--mode inference` + `--mode llm-judge` run to update numbers.

---

## 🗂️ Stage-by-Stage Command Reference

### Stage 0 — Environment Setup (One-Time)

```powershell
# Navigate to repo root
cd e:\Reply_agent

# Create virtual environment
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Copy env template and fill in your API key
copy .env.example .env
# Then edit .env and set: GROQ_API_KEY=gsk_your_key_here
```

**Prerequisites:** Python 3.10+. No GPU required.  
**API key needed for:** LLM judge live-scoring only (`--mode llm-judge`).

---

### Stage 1 — Dataset Inspection (Optional, Diagnostic)

```powershell
# Inspect the raw TWCS dataset and Spotify conversation profile
.venv\Scripts\python.exe -m src.inspect_dataset

# View data profile output
type results\data_profile.json
```

**Input:** `twcs.csv` (516 MB, ~3M tweets)  
**Output:** `results/data_profile.json` — brand distribution, conversation stats

---

### Stage 2 — Data Preparation (Reproducible From Scratch)

```powershell
# Prepare all Spotify knowledge, dev, and eval-pool partitions
.venv\Scripts\python.exe -m src.prepare_phase2_dataset

# Verify leakage report (should show 0 overlap across all partitions)
type results\phase2\leakage_report.json
```

**Output:**
- `data/processed/spotify_knowledge.jsonl` — 3,000 historical exchanges (TF-IDF training corpus)
- `data/processed/dev_inputs.jsonl` — 50 dev set model inputs
- `data/processed/eval_pool_inputs.jsonl` — 1,000 held-out eval candidates
- `data/manifests/split_manifest.jsonl` — complete provenance (4,050 records, seed=42)
- `results/phase2/exclusion_summary.json` — 1,182 exclusions by reason

> [!IMPORTANT]
> This stage needs the raw `twcs.csv` (516 MB). Skip if `data/processed/` already exists.

---

### Stage 3 — Build Baselines (Deterministic, No API Key)

```powershell
# Run baseline inference on all dev + eval records
.venv\Scripts\python.exe -m src.run_baselines

# Inspect baseline predictions
type results\phase4\baseline_predictions_dev.jsonl
```

**Output:**
- `results/phase4/baseline_0_predictions.jsonl` — Majority-class baseline
- `results/phase4/baseline_1_predictions.jsonl` — Rule-based keyword baseline

---

### Stage 4 — Main Agent Dev Tuning (Development Set)

```powershell
# Run Main Agent on 50 dev records for tuning / inspection
.venv\Scripts\python.exe -m src.run_phase5_dev

# Inspect dev predictions and ground-truth gold labels
type results\phase5\dev_predictions.jsonl
type dev_gold.jsonl
```

**Output:** `results/phase5/dev_predictions.jsonl` (50 records)  
**Purpose:** Tune intent thresholds, retrieval confidence cutoffs, and route rules.

---

### Stage 5 — Frozen Final Evaluation (200 Held-Out Records)

```powershell
# Run all 3 systems (Baseline 0, Baseline 1, Main Agent) on 200 eval records
.venv\Scripts\python.exe -m src.run_phase5_eval
# OR equivalently:
python reproduce.py --mode inference
```

**Output:**
- `results/phase5/eval_predictions_baseline0.jsonl`
- `results/phase5/eval_predictions_baseline1.jsonl`
- `results/phase5/eval_predictions_main_agent.jsonl`

**Runtime:** ~0.145 ms per item, ~0.09 seconds total. No API calls.

> [!CAUTION]
> This command overwrites the frozen prediction files. Only run if you intentionally want to  
> update predictions (e.g., after a pipeline change). Commit results before re-running.

---

### Stage 6A — Offline Classification Metrics (No API Key)

```powershell
# Recalculate intent accuracy, escalation recall, automation coverage
# Uses heuristic (keyword/regex) judge for reply quality — labeled clearly
python reproduce.py --mode offline
# OR equivalently:
python evaluate.py
```

**Output:** `metrics.json`, `results_table.csv`, `judge_agreement.json`  
**Time:** < 5 seconds  
**Judge mode label:** `judge_mode=heuristic` — NOT the same as LLM judgments.

---

### Stage 6B — LLM Judge Scoring (Requires API Key, ~15 min)

```powershell
# Score all 600 predictions (200 records × 3 systems) with LLM judge
# Results cached in results/phase6/llm_judge_cache.jsonl
python reproduce.py --mode llm-judge
# OR equivalently:
python evaluate.py --llm
```

**Prerequisites:** `GROQ_API_KEY` set in `.env`  
**Output:** `results/phase6/llm_judge_cache.jsonl` (with provenance: model ID, prompt SHA, input hash)  
**Cost:** ~600 API calls to `groq/compound`; typically $0.10–$0.50 at current rates.  
**Failure handling:** Failed calls are recorded explicitly; heuristic scores never silently substituted.

---

### Stage 6C — Offline Cached-Judge Metrics (Reviewer Mode, No API Key)

```powershell
# Recompute LLM-graded metrics from saved judge cache — no API calls
python reproduce.py --mode cached-judge
# OR equivalently:
python evaluate.py --cached-judge
```

**Requires:** `results/phase6/llm_judge_cache.jsonl` already populated (run Stage 6B first).  
**Output:** `metrics.json` labeled `judge_mode=llm_cached`, `results_table.csv`  
**Time:** < 1 minute  
**For reviewers:** This is the intended 15-minute reproduction path.

---

### Stage 7 — Human Annotation Review (Manual Step)

```powershell
# Export human review workbook (already done — v2 is the current version)
# The workbook is at: results/phase6/reply_human_review_task_v2.xlsx

# Import completed human ratings back into human_ratings.csv
.venv\Scripts\python.exe scratch\import_human_ratings.py

# Validate annotation completeness and consistency
python validate_annotations.py
```

**Input:** `reply_human_review_task_v2_annonated.xlsx` (completed by human reviewer)  
**Output:** `human_ratings.csv` (90 blinded reply ratings), `judge_agreement.json`

---

### Stage 8 — Run Full Test Suite

```powershell
python reproduce.py --mode test
# OR equivalently:
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

**Current result:** ✅ **154 passed, 0 failed** in ~66 seconds  
**Coverage:** 15 test files — unit tests for baselines, pipeline, phase2 data prep, phase6 metrics, kappa, extraction, redaction, language filter, duplicate detection.

---

### Stage 9 — Interactive Demo

```powershell
# Run the interactive live inference demo (single message → agent response)
.venv\Scripts\python.exe demo.py
```

**Input:** Prompts for a customer tweet interactively  
**Output:** Prints classified intent, routing decision, reply draft, and evidence citations

---

### Stage 10 — Run LLM Judge in Batched Mode (Optional, Robust)

```powershell
# Run judge in batched mode with retry logic (recommended for large runs)
.venv\Scripts\python.exe run_judge_batched.py

# View batched judge output
type results\phase6\llm_judge_predictions_600.jsonl
```

---

## 🔁 Complete End-to-End Reproduction (Fresh Machine)

```powershell
# 1. Setup
cd e:\Reply_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# → edit .env: set GROQ_API_KEY=gsk_...

# 2. Run inference (all 3 systems, 200 records)
python reproduce.py --mode inference

# 3. Score with LLM judge (requires API key, ~15 min)
python reproduce.py --mode llm-judge

# 4. Compute metrics from cache (no API key, < 1 min)
python reproduce.py --mode cached-judge

# 5. Run tests
python reproduce.py --mode test
```

**Total time including LLM judge:** ~20–25 minutes  
**Total time offline only:** < 5 minutes

---

## ⚡ Quick Reviewer Reproduction (Under 15 Minutes, No API Key)

```powershell
cd e:\Reply_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python reproduce.py --mode cached-judge    # < 1 min — LLM-graded metrics from cache
python reproduce.py --mode offline         # < 5 sec — classification/routing metrics
.venv\Scripts\python.exe -m pytest -q      # ~66 sec — all 154 tests
```

---

## 📁 Key File Locations

| File | Purpose |
|---|---|
| [`golden_eval.jsonl`](file:///e:/Reply_agent/golden_eval.jsonl) | 200 hand-labelled gold evaluation records |
| [`dev_gold.jsonl`](file:///e:/Reply_agent/dev_gold.jsonl) | 50 development gold records |
| [`metrics.json`](file:///e:/Reply_agent/metrics.json) | Computed metrics with Wilson 95% CIs |
| [`results_table.csv`](file:///e:/Reply_agent/results_table.csv) | Side-by-side comparison of all 3 systems |
| [`judge_agreement.json`](file:///e:/Reply_agent/judge_agreement.json) | Human–LLM judge κ and agreement stats |
| [`human_ratings.csv`](file:///e:/Reply_agent/human_ratings.csv) | 90 blinded human reply quality ratings |
| [`final_report.md`](file:///e:/Reply_agent/final_report.md) | Full 6-section evaluation report |
| [`decision_log.md`](file:///e:/Reply_agent/decision_log.md) | 12 non-obvious decision log entries |
| [`annotation_guidelines.md`](file:///e:/Reply_agent/annotation_guidelines.md) | Frozen v1.0 annotation guidelines |
| [`sampling_notes.md`](file:///e:/Reply_agent/sampling_notes.md) | Sampling strategy + test-retest log |
| [`intents.yaml`](file:///e:/Reply_agent/intents.yaml) | Frozen 8-intent taxonomy |
| [`results/phase6/llm_judge_cache.jsonl`](file:///e:/Reply_agent/results/phase6/llm_judge_cache.jsonl) | LLM judge cache (provenance-tracked) |
| [`results/phase6/judge_validation_agreement.md`](file:///e:/Reply_agent/results/phase6/judge_validation_agreement.md) | Human–judge agreement analysis |

---

## ⚠️ Known Issues & Next Actions

### Issue 1: LLM Judge Cache at 73.5% (441/600)
**Symptom:** `python reproduce.py --mode cached-judge` prints `[WARNING] Missing from cache: 159`  
**Fix:** Run `python reproduce.py --mode llm-judge` with a valid `GROQ_API_KEY` in `.env`

### Issue 2: Main Agent v1 High Critical Error Rate (23.5%)
**Root cause:** Low-quality historical tweet text passed as replies at low retrieval confidence  
**Fix implemented:** v2 improvements in `src/pipeline.py` (raised threshold 0.15→0.25, reply formatter, semantic fallback)  
**Next step:** Run `--mode inference` then `--mode llm-judge` to produce updated v2 numbers

### Issue 3: Human–Judge κ Near-Zero on Quality Dimensions
**Root cause:** Underspecified rubric anchors in LLM judge prompt v1  
**Fix implemented:** `prompts/llm_judge_prompt_v2.txt` with few-shot calibration examples  
**Next step:** Re-run judge with `LLM_JUDGE_PROMPT=v2` and collect fresh human ratings

---

## 🎯 Deliverables Checklist

| Deliverable | Status | File |
|---|---|---|
| ✅ Runnable pipeline (< 15 min reproduction) | **Done** | `reproduce.py` |
| ✅ Golden evaluation set (150–250 hand-labelled) | **Done** | `golden_eval.jsonl` (200) |
| ✅ Evaluation harness (automated + LLM judge) | **Done** | `evaluate.py`, `llm_judge.py` |
| ✅ LLM-as-judge rubric | **Done** | `results/phase6/judge_rubric.md` |
| ✅ Human–judge agreement evidence | **Done** | `judge_agreement.json`, `judge_validation_agreement.md` |
| ✅ Report: Problem framing | **Done** | `final_report.md` §1 |
| ✅ Report: Results vs. 2 baselines | **Done** | `final_report.md` §4 |
| ✅ Report: Failure analysis (top 5) | **Done** | `final_report.md` §5 |
| ✅ Report: Misleading headline section | **Done** | `final_report.md` §6.1 |
| ✅ Report: Next week roadmap | **Done** | `final_report.md` §6.3 |
| ✅ Decision log (10–15 items) | **Done** | `decision_log.md` (12 items) |
| ⚠️ Full LLM judge cache (100% coverage) | **Partial** | 441/600 — needs `--mode llm-judge` |
