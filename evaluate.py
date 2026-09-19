"""
evaluate.py — System Evaluation Pipeline

Usage
-----
python evaluate.py
    Compute classification/routing metrics.
    Reply-quality scores use the HEURISTIC judge (judge.py).
    Scores are clearly labeled judge_type=heuristic in all outputs.

python evaluate.py --llm
    Run the actual LLM judge (llm_judge.py) for reply-quality scoring.
    Results cached in results/phase6/llm_judge_cache.jsonl with full provenance.
    Requires GROQ_API_KEY (or configured provider key) in .env.
    Coverage reported: succeeded / failed / coverage%.
    NEVER silently substitutes heuristic scores on failure.

python evaluate.py --cached-judge
    Recompute metrics from saved LLM judgments (no API calls).
    Rejects stale cache entries (reply, evidence, or config changed).
    Designed for offline reproduction by reviewers without API credentials.
"""

import json
import csv
import math
import random
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter

import pandas as pd

ROOT = Path(__file__).parent
EVAL_GOLD_PATH = ROOT / "golden_eval.jsonl"
PHASE5_RESULTS_DIR = ROOT / "results/phase5"
PHASE6_DIR = ROOT / "results/phase6"


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def wilson_ci(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """Wilson score confidence interval for proportions."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    z = 1.96
    denom = 1 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    margin = (z / denom) * math.sqrt((p * (1 - p) / n) + ((z**2) / (4 * (n**2))))
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return round(p, 4), round(low, 4), round(high, 4)


def calculate_linear_weighted_kappa(
    ratings1: List[int], ratings2: List[int], min_val: int = 0, max_val: int = 2
) -> Tuple[float, float]:
    """Linear-weighted Cohen's Kappa calculation."""
    assert len(ratings1) == len(ratings2), "Lengths must match"
    n = len(ratings1)
    if n == 0:
        return 1.0, 1.0

    exact_matches = sum(1 for a, b in zip(ratings1, ratings2) if a == b)
    exact_agreement = exact_matches / n

    scale_range = max_val - min_val if max_val > min_val else 1
    counts: Dict[Tuple[int, int], int] = {}
    row_sums: Counter = Counter()
    col_sums: Counter = Counter()

    for a, b in zip(ratings1, ratings2):
        counts[(a, b)] = counts.get((a, b), 0) + 1
        row_sums[a] += 1
        col_sums[b] += 1

    P_o = 0.0
    P_e = 0.0
    for i in range(min_val, max_val + 1):
        for j in range(min_val, max_val + 1):
            w_ij = 1.0 - (abs(i - j) / scale_range)
            p_ij = counts.get((i, j), 0) / n
            p_i_dot = row_sums[i] / n
            p_dot_j = col_sums[j] / n
            P_o += w_ij * p_ij
            P_e += w_ij * (p_i_dot * p_dot_j)

    kappa = 1.0 if P_e == 1.0 else (P_o - P_e) / (1.0 - P_e)
    return round(exact_agreement, 4), round(kappa, 4)


def cluster_bootstrap_ci(
    sample_groups: Dict[str, List[Dict[str, Any]]], num_bootstraps: int = 1000
) -> Dict[str, Tuple[float, float]]:
    """Cluster bootstrap resampling at message level (30 clusters × 3 replies = 90)."""
    random.seed(42)
    group_keys = list(sample_groups.keys())

    rel_s, grd_s, use_s, tone_s = [], [], [], []
    for _ in range(num_bootstraps):
        resampled_keys = random.choices(group_keys, k=len(group_keys))
        items = [item for k in resampled_keys for item in sample_groups[k]]
        N = len(items)
        rel_s.append(sum(r["judge_scores"]["relevance"] for r in items) / N)
        grd_s.append(sum(r["judge_scores"]["grounding"] for r in items) / N)
        use_s.append(sum(r["judge_scores"]["usefulness"] for r in items) / N)
        tone_s.append(sum(r["judge_scores"]["tone"] for r in items) / N)

    for lst in [rel_s, grd_s, use_s, tone_s]:
        lst.sort()
    lo, hi = int(0.025 * num_bootstraps), int(0.975 * num_bootstraps)
    return {
        "relevance_ci": (round(rel_s[lo], 2), round(rel_s[hi], 2)),
        "grounding_ci": (round(grd_s[lo], 2), round(grd_s[hi], 2)),
        "usefulness_ci": (round(use_s[lo], 2), round(use_s[hi], 2)),
        "tone_ci": (round(tone_s[lo], 2), round(tone_s[hi], 2)),
    }


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------

def _load_gold() -> Dict[str, Dict]:
    with open(EVAL_GOLD_PATH, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    gold_map = {r["example_id"]: r for r in records}
    assert len(gold_map) == 200, f"Expected 200 gold records, got {len(gold_map)}"
    return gold_map


def _load_system_predictions() -> Dict[str, List[Dict]]:
    system_files = {
        "baseline_0_majority": PHASE5_RESULTS_DIR / "eval_predictions_baseline_0.jsonl",
        "baseline_1_rules": PHASE5_RESULTS_DIR / "eval_predictions_baseline_1.jsonl",
        "main_agent_v1": PHASE5_RESULTS_DIR / "eval_predictions_main_agent.jsonl",
    }
    joined: Dict[str, List[Dict]] = {}
    for sys_key, fpath in system_files.items():
        assert fpath.exists(), f"Missing prediction file: {fpath}"
        preds = [json.loads(line) for line in fpath.read_text(encoding="utf-8").strip().split("\n")]
        pred_ids = [p["example_id"] for p in preds]
        assert len(pred_ids) == 200, f"Expected 200 predictions for {sys_key}, got {len(pred_ids)}"
        assert len(set(pred_ids)) == 200, f"Duplicate example_ids in {sys_key}"
        joined[sys_key] = preds
    print("[OK] Joined 600 predictions (200 x 3 systems) to gold labels with 0 missing/duplicate joins.")
    return joined


def _build_retrieved_evidence_lookup() -> Dict[str, str]:
    """
    Build a lookup from (example_id, system_id) → retrieved_evidence string
    from the frozen judge_predictions_600.jsonl (which stores heuristic scores but
    also has retrieved_source_ids from the main agent predictions).

    For the LLM judge, we read retrieved_source_ids from phase5 main_agent predictions
    and pass them as evidence context.
    """
    lookup: Dict[str, str] = {}
    # Load main_agent predictions which carry retrieved_source_ids
    main_preds_path = PHASE5_RESULTS_DIR / "eval_predictions_main_agent.jsonl"
    if main_preds_path.exists():
        preds = [json.loads(l) for l in main_preds_path.read_text(encoding="utf-8").strip().split("\n")]
        for p in preds:
            eid = p["example_id"]
            source_ids = p.get("retrieved_source_ids", [])
            lookup[eid] = ", ".join(source_ids) if source_ids else "(none)"
    return lookup


# ---------------------------------------------------------------------------
# Heuristic scoring (score 600 records with RubricJudge)
# ---------------------------------------------------------------------------

def _score_heuristic(
    joined_data: Dict[str, List[Dict]], gold_map: Dict[str, Dict]
) -> List[Dict]:
    from judge import RubricJudge
    judge = RubricJudge()
    scored = []
    for sys_key, preds in joined_data.items():
        for pred in preds:
            ex_id = pred["example_id"]
            gold = gold_map[ex_id]
            scores = judge.evaluate_reply(
                customer_message=gold["message"],
                predicted_intent=pred["predicted_intent"],
                predicted_must_escalate=pred["predicted_must_escalate"],
                predicted_reply=pred["predicted_reply"],
                gold_must_escalate=gold["must_escalate"],
            )
            scored.append({
                "example_id": ex_id,
                "system_id": sys_key,
                "subset": gold["subset"],
                "intent_gold": gold["intent"],
                "intent_pred": pred["predicted_intent"],
                "escalate_gold": gold["must_escalate"],
                "escalate_pred": pred["predicted_must_escalate"],
                "predicted_reply": pred["predicted_reply"],
                "judge_type": "heuristic",    # Always labeled
                "judge_scores": scores,
            })
    return scored


# ---------------------------------------------------------------------------
# LLM scoring (score 600 records with LLMRubricJudge)
# ---------------------------------------------------------------------------

def _score_llm(
    joined_data: Dict[str, List[Dict]],
    gold_map: Dict[str, Dict],
    evidence_lookup: Dict[str, str],
) -> Tuple[List[Dict], int, int]:
    """
    Score 600 records via LLM. Returns (scored_list, num_success, num_failed).
    Failures are recorded explicitly — heuristic scores are NEVER substituted.
    """
    from llm_judge import LLMRubricJudge
    judge = LLMRubricJudge()

    scored = []
    num_success = 0
    num_failed = 0

    total = sum(len(preds) for preds in joined_data.values())
    done = 0

    for sys_key, preds in joined_data.items():
        for pred in preds:
            ex_id = pred["example_id"]
            gold = gold_map[ex_id]
            done += 1

            result = judge.evaluate_reply(
                customer_message=gold["message"],
                predicted_intent=pred["predicted_intent"],
                predicted_must_escalate=pred["predicted_must_escalate"],
                predicted_reply=pred["predicted_reply"],
                gold_must_escalate=gold["must_escalate"],
                prior_context=gold.get("prior_context", ""),
                retrieved_evidence=evidence_lookup.get(ex_id, "(none)"),
            )

            if result.get("llm_failure"):
                num_failed += 1
                entry = {
                    "example_id": ex_id,
                    "system_id": sys_key,
                    "subset": gold["subset"],
                    "intent_gold": gold["intent"],
                    "intent_pred": pred["predicted_intent"],
                    "escalate_gold": gold["must_escalate"],
                    "escalate_pred": pred["predicted_must_escalate"],
                    "predicted_reply": pred["predicted_reply"],
                    "judge_type": "llm_failure",
                    "llm_failure": True,
                    "failure_reason": result.get("failure_reason"),
                    "model_id": result.get("model_id"),
                    "cache_key": result.get("cache_key"),
                    "judge_scores": None,   # Explicitly None — not heuristic
                }
            else:
                num_success += 1
                entry = {
                    "example_id": ex_id,
                    "system_id": sys_key,
                    "subset": gold["subset"],
                    "intent_gold": gold["intent"],
                    "intent_pred": pred["predicted_intent"],
                    "escalate_gold": gold["must_escalate"],
                    "escalate_pred": pred["predicted_must_escalate"],
                    "predicted_reply": pred["predicted_reply"],
                    "judge_type": "llm",
                    "from_cache": result.get("from_cache", False),
                    "model_id": result.get("model_id"),
                    "prompt_version": result.get("prompt_version"),
                    "rubric_sha256": result.get("rubric_sha256"),
                    "cache_key": result.get("cache_key"),
                    "judge_scores": {
                        "relevance": result["relevance"],
                        "grounding": result["grounding"],
                        "usefulness": result["usefulness"],
                        "tone": result["tone"],
                        "critical_error": result["critical_error"],
                        "critical_details": result.get("critical_details", {}),
                    },
                    "rationales": result.get("rationales", {}),
                }

            scored.append(entry)
            from_cache_label = "(cache)" if result.get("from_cache") else "(live)"
            status = "FAIL" if result.get("llm_failure") else "OK"
            print(f"  [{done}/{total}] {status} {from_cache_label} {ex_id} [{sys_key}]")

    return scored, num_success, num_failed


# ---------------------------------------------------------------------------
# Load-from-cache mode (--cached-judge)
# ---------------------------------------------------------------------------

def _load_from_llm_cache(
    joined_data: Dict[str, List[Dict]],
    gold_map: Dict[str, Dict],
    evidence_lookup: Dict[str, str],
) -> Tuple[List[Dict], int, int, int]:
    """
    Reconstruct 600 scored records entirely from cache. No API calls.
    Stale entries (cache_key mismatch) are counted and reported.
    Returns (scored_list, num_hit, num_stale, num_missing).
    """
    from llm_judge import LLMRubricJudge, _make_cache_key, _sha256, _load_text, RUBRIC_PATH, PROMPT_PATH, _load_cache, CACHE_PATH

    if not CACHE_PATH.exists():
        print(f"[ERROR] LLM judge cache not found: {CACHE_PATH}")
        print("        Run 'python evaluate.py --llm' first to populate the cache.")
        sys.exit(1)

    rubric_sha256 = _sha256(_load_text(RUBRIC_PATH))
    prompt_sha256 = _sha256(_load_text(PROMPT_PATH))

    # Detect model/judge config
    from configs.settings import settings
    provider = settings.llm_provider
    model = getattr(settings, "llm_judge_model", "compound")
    model_id = f"{provider}/{model}"

    cache = _load_cache(CACHE_PATH)

    scored = []
    num_hit = 0
    num_stale = 0
    num_missing = 0

    for sys_key, preds in joined_data.items():
        for pred in preds:
            ex_id = pred["example_id"]
            gold = gold_map[ex_id]
            routing_decision = "escalate" if pred["predicted_must_escalate"] else "auto_handle"
            prior_context = gold.get("prior_context", "")
            retrieved_evidence = evidence_lookup.get(ex_id, "(none)")

            expected_key = _make_cache_key(
                customer_message=gold["message"],
                prior_context=prior_context,
                retrieved_evidence=retrieved_evidence,
                routing_decision=routing_decision,
                predicted_reply=pred["predicted_reply"],
                model_id=model_id,
                rubric_sha256=rubric_sha256,
                prompt_sha256=prompt_sha256,
            )

            if expected_key not in cache:
                num_missing += 1
                scored.append({
                    "example_id": ex_id,
                    "system_id": sys_key,
                    "subset": gold["subset"],
                    "intent_gold": gold["intent"],
                    "intent_pred": pred["predicted_intent"],
                    "escalate_gold": gold["must_escalate"],
                    "escalate_pred": pred["predicted_must_escalate"],
                    "predicted_reply": pred["predicted_reply"],
                    "judge_type": "cache_missing",
                    "judge_scores": None,
                })
                continue

            entry = cache[expected_key]

            # Staleness check: rubric or prompt SHA changed
            if (entry.get("rubric_sha256") != rubric_sha256 or
                    entry.get("prompt_sha256") != prompt_sha256):
                num_stale += 1
                print(f"  [STALE] Cache entry for {ex_id}/{sys_key}: rubric or prompt has changed. Skipping.")
                scored.append({
                    "example_id": ex_id,
                    "system_id": sys_key,
                    "subset": gold["subset"],
                    "intent_gold": gold["intent"],
                    "intent_pred": pred["predicted_intent"],
                    "escalate_gold": gold["must_escalate"],
                    "escalate_pred": pred["predicted_must_escalate"],
                    "predicted_reply": pred["predicted_reply"],
                    "judge_type": "cache_stale",
                    "judge_scores": None,
                })
                continue

            if entry.get("llm_failure"):
                scored.append({
                    "example_id": ex_id,
                    "system_id": sys_key,
                    "subset": gold["subset"],
                    "intent_gold": gold["intent"],
                    "intent_pred": pred["predicted_intent"],
                    "escalate_gold": gold["must_escalate"],
                    "escalate_pred": pred["predicted_must_escalate"],
                    "predicted_reply": pred["predicted_reply"],
                    "judge_type": "llm_failure",
                    "llm_failure": True,
                    "failure_reason": entry.get("failure_reason"),
                    "judge_scores": None,
                })
                num_stale += 0  # Failures do not count as stale
                num_missing += 0
                num_hit += 1
                continue

            s = entry.get("scores", {})
            num_hit += 1
            scored.append({
                "example_id": ex_id,
                "system_id": sys_key,
                "subset": gold["subset"],
                "intent_gold": gold["intent"],
                "intent_pred": pred["predicted_intent"],
                "escalate_gold": gold["must_escalate"],
                "escalate_pred": pred["predicted_must_escalate"],
                "predicted_reply": pred["predicted_reply"],
                "judge_type": "llm",
                "from_cache": True,
                "model_id": entry.get("model_id"),
                "prompt_version": entry.get("prompt_version"),
                "rubric_sha256": entry.get("rubric_sha256"),
                "cache_key": expected_key,
                "judge_scores": {
                    "relevance": s.get("relevance"),
                    "grounding": s.get("grounding"),
                    "usefulness": s.get("usefulness"),
                    "tone": s.get("tone"),
                    "critical_error": s.get("critical_error"),
                    "critical_details": s.get("critical_details", {}),
                },
                "rationales": s.get("rationales", {}),
            })

    return scored, num_hit, num_stale, num_missing


# ---------------------------------------------------------------------------
# Human agreement computation
# ---------------------------------------------------------------------------

def _compute_human_agreement(scored_600: List[Dict]) -> Dict:
    """Read human_ratings.csv and compute agreement against LLM or heuristic scores.
    Never manufactures ratings. Returns status dict."""
    human_ratings_path = ROOT / "human_ratings.csv"
    has_completed = False
    human_ratings = []
    message_groups: Dict[str, List[Dict]] = {}

    if human_ratings_path.exists():
        df_human = pd.read_csv(human_ratings_path, dtype=str, keep_default_na=False)
        required_cols = ["relevance_human", "grounding_human", "usefulness_human",
                         "tone_human", "critical_error_human"]
        if all(col in df_human.columns for col in required_cols):
            filled_mask = (
                df_human["relevance_human"].str.strip().ne("") &
                df_human["grounding_human"].str.strip().ne("") &
                df_human["usefulness_human"].str.strip().ne("") &
                df_human["tone_human"].str.strip().ne("") &
                df_human["critical_error_human"].str.strip().ne("")
            )
            if filled_mask.sum() == len(df_human) and len(df_human) == 90:
                has_completed = True
                print(f"[OK] Found 90 independently completed human ratings.")

                # Merge system identity mapping if system_id is blinded
                if "system_id" not in df_human.columns:
                    mapping_path = PHASE6_DIR / "system_identity_mapping.csv"
                    if mapping_path.exists():
                        df_map = pd.read_csv(mapping_path, dtype=str)
                        df_human = df_human.merge(df_map[["review_id", "system_id"]], on="review_id", how="left")

                scored_lookup = {
                    (r["example_id"], r["system_id"]): r for r in scored_600
                }
                for _, h_row in df_human.iterrows():
                    ex_id = h_row["example_id"]
                    sys_id = h_row.get("system_id")
                    pred_item = scored_lookup.get((ex_id, sys_id))
                    if pred_item is None or pred_item.get("judge_scores") is None:
                        continue  # Skip if no judge score for this row
                    row_data = {
                        "example_id": ex_id,
                        "system_id": sys_id,
                        "relevance_human": int(h_row["relevance_human"]),
                        "grounding_human": int(h_row["grounding_human"]),
                        "usefulness_human": int(h_row["usefulness_human"]),
                        "tone_human": int(h_row["tone_human"]),
                        "critical_error_human": int(
                            1 if str(h_row["critical_error_human"]).lower() in ["1", "true"] else 0
                        ),
                        "relevance_judge": pred_item["judge_scores"]["relevance"],
                        "grounding_judge": pred_item["judge_scores"]["grounding"],
                        "usefulness_judge": pred_item["judge_scores"]["usefulness"],
                        "tone_judge": pred_item["judge_scores"]["tone"],
                        "critical_error_judge": int(1 if pred_item["judge_scores"]["critical_error"] else 0),
                        "judge_type": pred_item.get("judge_type", "unknown"),
                        "judge_scores": pred_item["judge_scores"],
                    }
                    human_ratings.append(row_data)
                    if ex_id not in message_groups:
                        message_groups[ex_id] = []
                    message_groups[ex_id].append(row_data)

    if has_completed and human_ratings:
        judge_type_used = human_ratings[0].get("judge_type", "unknown")
        dims = ["relevance", "grounding", "usefulness", "tone"]
        kappa_output = {
            "status": "Measured",
            "judge_type_compared": judge_type_used,
            "dimensions": {},
        }
        for d in dims:
            h_v = [r[f"{d}_human"] for r in human_ratings]
            j_v = [r[f"{d}_judge"] for r in human_ratings]
            exact_acc, kappa_val = calculate_linear_weighted_kappa(h_v, j_v)
            kappa_output["dimensions"][d] = {
                "status": "Measured",
                "exact_agreement": exact_acc,
                "linear_weighted_kappa": kappa_val,
            }
        h_c = [r["critical_error_human"] for r in human_ratings]
        j_c = [r["critical_error_judge"] for r in human_ratings]
        c_acc, c_kappa = calculate_linear_weighted_kappa(h_c, j_c, min_val=0, max_val=1)
        kappa_output["dimensions"]["critical_error"] = {
            "status": "Measured",
            "exact_agreement": c_acc,
            "linear_weighted_kappa": c_kappa,
            "tp": sum(1 for a, b in zip(h_c, j_c) if a == 1 and b == 1),
            "fp": sum(1 for a, b in zip(h_c, j_c) if a == 0 and b == 1),
            "fn": sum(1 for a, b in zip(h_c, j_c) if a == 1 and b == 0),
            "tn": sum(1 for a, b in zip(h_c, j_c) if a == 0 and b == 0),
        }
        if message_groups:
            kappa_output["grouped_uncertainty_ci_95"] = cluster_bootstrap_ci(message_groups)
    else:
        print("[NOTICE] Independent human ratings not yet completed.")
        print("         Human review columns remain empty pending independent human review.")
        print("         Agreement is honestly reported as 'Not yet measured'.")
        kappa_output = {
            "status": "Not yet measured",
            "message": (
                "Human inter-rater agreement has not yet been measured. "
                "Awaiting independently completed human ratings via "
                "results/phase6/reply_human_review_task_v2.xlsx or human_ratings.csv."
            ),
            "review_sample_size": 90,
            "clusters_count": 30,
            "exact_agreement": "Not yet measured",
            "linear_weighted_kappa": "Not yet measured",
            "dimensions": {
                d: {"status": "Not yet measured", "exact_agreement": None, "linear_weighted_kappa": None}
                for d in ["relevance", "grounding", "usefulness", "tone", "critical_error"]
            },
        }
    return kappa_output


# ---------------------------------------------------------------------------
# Metrics summary computation
# ---------------------------------------------------------------------------

def _compute_metrics(
    scored_600: List[Dict],
    judge_mode: str,
    coverage_info: Optional[Dict] = None,
) -> Tuple[Dict, List[Dict]]:
    """Compute per-system metrics. Only uses rows that have actual judge_scores."""
    metrics_summary: Dict[str, Any] = {
        "judge_mode": judge_mode,
        "coverage": coverage_info or {},
        "systems": {},
    }
    table_rows = []

    for sys_id, sys_name in [
        ("baseline_0_majority", "Baseline 0"),
        ("baseline_1_rules", "Baseline 1"),
        ("main_agent_v1", "Main Agent"),
    ]:
        preds = [p for p in scored_600 if p["system_id"] == sys_id]
        N = len(preds)

        # Classification / routing metrics — all 200 rows
        intent_corr = sum(1 for p in preds if p["intent_gold"] == p["intent_pred"])
        int_acc, int_low, int_high = wilson_ci(intent_corr, N)

        req_review_gold = [p for p in preds if p["escalate_gold"] is True]
        num_req = len(req_review_gold)
        req_esc = sum(1 for p in req_review_gold if p["escalate_pred"] is True)
        esc_rec, esc_low, esc_high = wilson_ci(req_esc, num_req)

        auto_replies = [p for p in preds if p["escalate_pred"] is False]
        num_auto = len(auto_replies)
        cov, cov_low, cov_high = wilson_ci(num_auto, N)

        # Reply-quality metrics — only rows with valid judge_scores
        scored_preds = [p for p in preds if p.get("judge_scores") is not None]
        n_scored = len(scored_preds)
        n_unscored = N - n_scored

        if n_scored > 0:
            avg_rel = round(sum(p["judge_scores"]["relevance"] for p in scored_preds) / n_scored, 2)
            avg_grd = round(sum(p["judge_scores"]["grounding"] for p in scored_preds) / n_scored, 2)
            avg_use = round(sum(p["judge_scores"]["usefulness"] for p in scored_preds) / n_scored, 2)
            avg_tone = round(sum(p["judge_scores"]["tone"] for p in scored_preds) / n_scored, 2)
            num_crit = sum(1 for p in scored_preds if p["judge_scores"]["critical_error"])

            unsafe_auto = [
                p for p in auto_replies
                if (p["escalate_gold"] is True) or (
                    p.get("judge_scores") is not None and p["judge_scores"]["critical_error"]
                )
            ]
            num_unsafe = len(unsafe_auto)
            if num_auto > 0:
                unsafe_rate, unsafe_low, unsafe_high = wilson_ci(num_unsafe, num_auto)
                unsafe_str = f"{unsafe_rate * 100:.1f}% ({num_unsafe}/{num_auto})"
            else:
                unsafe_str = "N/A (0 automated)"

            quality_note = (
                f"Scored {n_scored}/{N} rows ({judge_mode})"
                + (f"; {n_unscored} rows unscored (LLM failure)" if n_unscored > 0 else "")
            )
        else:
            avg_rel = avg_grd = avg_use = avg_tone = None
            num_crit = 0
            unsafe_str = "N/A (no judge scores)"
            quality_note = f"0/{N} rows scored — all LLM calls failed"

        sys_metric = {
            "system_name": sys_name,
            "total_messages": N,
            "intent_accuracy": {"val": int_acc, "num": intent_corr, "denom": N, "ci_95": [int_low, int_high]},
            "escalation_recall": {"val": esc_rec, "num": req_esc, "denom": num_req, "ci_95": [esc_low, esc_high]},
            "automation_coverage": {"val": cov, "num": num_auto, "denom": N, "ci_95": [cov_low, cov_high]},
            "unsafe_automation_rate": unsafe_str,
            "reply_quality_note": quality_note,
            "relevance_0_2": avg_rel,
            "grounding_0_2": avg_grd,
            "usefulness_0_2": avg_use,
            "tone_0_2": avg_tone,
            "critical_errors": {"num": num_crit, "denom": n_scored, "rate": round(num_crit / n_scored, 4) if n_scored else None},
        }
        metrics_summary["systems"][sys_id] = sys_metric

        table_rows.append({
            "system_id": sys_id,
            "system_name": sys_name,
            "judge_mode": judge_mode,
            "total_messages": N,
            "intent_accuracy": f"{int_acc * 100:.1f}% ({intent_corr}/{N})",
            "escalation_recall": f"{esc_rec * 100:.1f}% ({req_esc}/{num_req})",
            "automation_coverage": f"{cov * 100:.1f}% ({num_auto}/{N})",
            "unsafe_automation_rate": unsafe_str,
            "relevance": avg_rel,
            "grounding": avg_grd,
            "usefulness": avg_use,
            "tone": avg_tone,
            "critical_error_count": num_crit,
            "reply_quality_note": quality_note,
        })

    return metrics_summary, table_rows


# ---------------------------------------------------------------------------
# Main evaluation entry point
# ---------------------------------------------------------------------------

def run_evaluation(use_llm: bool = False, cached_judge: bool = False):
    """
    use_llm=False, cached_judge=False → heuristic judge (labeled heuristic)
    use_llm=True                      → live LLM judge
    cached_judge=True                 → read from LLM cache, no API calls
    """
    if use_llm and cached_judge:
        print("[ERROR] --llm and --cached-judge are mutually exclusive.")
        sys.exit(1)

    print("=== Running Complete Evaluation Pipeline ===")
    if use_llm:
        print("[MODE] LLM Judge (live API calls, results cached with provenance)")
    elif cached_judge:
        print("[MODE] Cached LLM Judge (offline — reading from saved LLM judgments, no API calls)")
        print("       This recomputes metrics from saved LLM judgments. Run 'python evaluate.py --llm'")
        print("       first to populate the cache, then share results/phase6/llm_judge_cache.jsonl")
        print("       with reviewers for offline reproduction.")
    else:
        print("[MODE] Heuristic Judge (classify/route metrics + heuristic reply scores, labeled heuristic)")
        print("       NOTE: Heuristic scores are keyword/regex-based and are NOT LLM judgments.")
        print("       Run 'python evaluate.py --llm' for actual LLM-based reply-quality evaluation.")

    gold_map = _load_gold()
    joined_data = _load_system_predictions()
    evidence_lookup = _build_retrieved_evidence_lookup()

    coverage_info = None

    if cached_judge:
        print("\n[INFO] Loading from LLM judge cache...")
        scored_600, num_hit, num_stale, num_missing = _load_from_llm_cache(
            joined_data, gold_map, evidence_lookup
        )
        judge_mode = "llm_cached"
        coverage_info = {
            "mode": "cached_judge",
            "total": 600,
            "cache_hit": num_hit,
            "stale": num_stale,
            "missing": num_missing,
            "coverage_pct": round(100.0 * num_hit / 600, 1),
        }
        print(f"\n[COVERAGE] Cache hits: {num_hit}/600 ({coverage_info['coverage_pct']}%)")
        if num_stale > 0:
            print(f"[WARNING]  Stale entries (rubric/prompt changed): {num_stale}")
        if num_missing > 0:
            print(f"[WARNING]  Missing from cache: {num_missing} — run 'python evaluate.py --llm' to score them.")

    elif use_llm:
        print("\n[INFO] Scoring 600 predictions with LLM judge (this may take several minutes)...")
        scored_600, num_success, num_failed = _score_llm(joined_data, gold_map, evidence_lookup)
        judge_mode = "llm"
        coverage_pct = round(100.0 * num_success / 600, 1) if 600 > 0 else 0.0
        coverage_info = {
            "mode": "llm",
            "total": 600,
            "succeeded": num_success,
            "failed": num_failed,
            "coverage_pct": coverage_pct,
        }
        print(f"\n[COVERAGE] LLM scoring: {num_success}/600 succeeded ({coverage_pct}%), {num_failed} failed")
        if num_failed > 0:
            print(f"[WARNING]  {num_failed} rows unscored due to LLM failures.")
            print("           Failures are recorded in results/phase6/llm_judge_cache.jsonl.")
            print("           These rows have judge_type=llm_failure and null judge_scores.")
            print("           Heuristic scores are NOT substituted.")

        # Write full LLM-scored predictions to separate file
        llm_out_path = PHASE6_DIR / "llm_judge_predictions_600.jsonl"
        with open(llm_out_path, "w", encoding="utf-8") as f:
            for row in scored_600:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"[OK] Saved LLM judge predictions -> {llm_out_path.name}")

    else:
        scored_600 = _score_heuristic(joined_data, gold_map)
        judge_mode = "heuristic"
        coverage_info = {
            "mode": "heuristic",
            "note": "Heuristic (keyword/regex) judge — NOT an LLM judgment. Run --llm for actual LLM scoring.",
        }

    # Human agreement
    kappa_output = _compute_human_agreement(scored_600)
    with open(ROOT / "judge_agreement.json", "w", encoding="utf-8") as f:
        json.dump(kappa_output, f, indent=2)
    print(f"[OK] Created judge_agreement.json (Status: {kappa_output['status']})")

    # Metrics
    metrics_summary, table_rows = _compute_metrics(scored_600, judge_mode, coverage_info)
    with open(ROOT / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print("[OK] Created metrics.json")

    df_table = pd.DataFrame(table_rows)
    df_table.to_csv(ROOT / "results_table.csv", index=False)
    print("[OK] Created results_table.csv")

    print("\nALL REQUIRED OUTPUT FILES CREATED SUCCESSFULLY!")
    if not use_llm and not cached_judge:
        print(
            "\n[REMINDER] Reply-quality scores above are HEURISTIC (keyword/regex-based).\n"
            "           They are not LLM judgments. Labels: judge_type=heuristic in metrics.json.\n"
            "           For LLM-graded reply quality, run: python evaluate.py --llm"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reply Agent Evaluation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--llm",
        action="store_true",
        help="Run LLM judge for reply-quality scoring (requires API key in .env).",
    )
    group.add_argument(
        "--cached-judge",
        action="store_true",
        dest="cached_judge",
        help=(
            "Recompute metrics from saved LLM judgments. No API calls. "
            "Stale cache entries (when reply/evidence/config changed) are rejected. "
            "Run 'python evaluate.py --llm' first to populate the cache."
        ),
    )
    args = parser.parse_args()
    run_evaluation(use_llm=args.llm, cached_judge=args.cached_judge)
