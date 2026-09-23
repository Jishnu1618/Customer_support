#!/usr/bin/env python3
"""
run_judge_batched.py — Batch LLM Judge Runner with Rate-Limit Handling and Resume Support.

This script evaluates all 600 predictions using the configured LLM judge,
respecting rate limits and resuming from cached results automatically.

Usage:
    python run_judge_batched.py --status
    python run_judge_batched.py --batch-size 50
    python run_judge_batched.py --provider groq --model openai/gpt-oss-120b --batch-size 100 --delay 2.0
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent


def get_cache_coverage(model_id: str):
    """Count successful cache entries for the specified model_id."""
    from llm_judge import _load_cache, CACHE_PATH

    if not CACHE_PATH.exists():
        return 0, 0, 0

    cache = _load_cache(CACHE_PATH)
    all_entries = list(cache.values())
    matching = [e for e in all_entries if e.get("model_id") == model_id]
    success = [e for e in matching if not e.get("llm_failure")]
    failures = [e for e in matching if e.get("llm_failure")]
    return len(success), len(failures), len(all_entries)


def parse_retry_delay(error_str: str) -> float:
    """Extract retryDelay seconds from 429 error response."""
    err = str(error_str)
    # Groq format: "Please try again in 4m3.21s" or "try again in 3.75s"
    groq_match = re.search(r"try again in\s+(?:(\d+)m)?(\d+(?:\.\d+)?)s", err, re.IGNORECASE)
    if groq_match:
        mins = float(groq_match.group(1)) if groq_match.group(1) else 0.0
        secs = float(groq_match.group(2))
        return mins * 60.0 + secs + 2.0
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", err)
    if match:
        return float(match.group(1)) + 1.0
    return 15.0


def run_batch(
    provider: str,
    model: str,
    batch_size: int = 50,
    min_delay: float = 2.0,
    verbose: bool = True,
):
    """
    Run up to batch_size new LLM judge calls.
    Returns (num_new_success, num_new_fail, total_done).
    """
    from llm_judge import (
        LLMRubricJudge, _make_cache_key, _load_cache, _load_text,
        _sha256, CACHE_PATH, RUBRIC_PATH, PROMPT_PATH
    )
    from evaluate import _load_gold, _load_system_predictions, _build_retrieved_evidence_lookup

    model_id = f"{provider}/{model}"

    if verbose:
        print(f"[INFO] Provider: {provider}, Model: {model}", flush=True)
        print(f"[INFO] model_id for cache: {model_id}", flush=True)

    judge = LLMRubricJudge(provider=provider, model=model)
    gold_map = _load_gold()
    joined_data = _load_system_predictions()
    evidence_lookup = _build_retrieved_evidence_lookup()

    rubric_sha256 = _sha256(_load_text(RUBRIC_PATH))
    prompt_sha256 = _sha256(_load_text(PROMPT_PATH))

    # Build set of cache keys already successfully computed for this model
    cache = _load_cache(CACHE_PATH)
    done_keys = set(
        k for k, e in cache.items()
        if e.get("model_id") == model_id and not e.get("llm_failure")
    )

    if verbose:
        print(f"[INFO] Already done ({model_id}): {len(done_keys)}/600", flush=True)

    # Build all 600 jobs
    all_jobs = []
    for sys_key, preds in joined_data.items():
        for pred in preds:
            ex_id = pred["example_id"]
            gold = gold_map[ex_id]
            all_jobs.append({
                "ex_id": ex_id,
                "sys_key": sys_key,
                "pred": pred,
                "gold": gold,
                "evidence": evidence_lookup.get(ex_id, "(none)"),
            })

    # Filter out already-done jobs
    pending = []
    for job in all_jobs:
        routing_decision = "escalate" if job["pred"]["predicted_must_escalate"] else "auto_handle"
        ck = _make_cache_key(
            customer_message=job["gold"]["message"],
            prior_context=job["gold"].get("prior_context", ""),
            retrieved_evidence=job["evidence"],
            routing_decision=routing_decision,
            predicted_reply=job["pred"]["predicted_reply"],
            model_id=model_id,
            rubric_sha256=rubric_sha256,
            prompt_sha256=prompt_sha256,
        )
        if ck not in done_keys:
            pending.append((ck, job))

    # Prioritize the 90 human review rows to unblock human agreement computation
    mapping_path = ROOT / "results" / "phase6" / "system_identity_mapping.csv"
    if mapping_path.exists():
        import pandas as pd
        df_map = pd.read_csv(mapping_path)
        review_pairs = set(zip(df_map["example_id"], df_map["system_id"]))
        pending.sort(key=lambda item: 0 if (item[1]["ex_id"], item[1]["sys_key"]) in review_pairs else 1)
        pending_review = sum(1 for item in pending if (item[1]["ex_id"], item[1]["sys_key"]) in review_pairs)
        if verbose:
            print(f"[INFO] Prioritized {pending_review} pending human review items to the front of queue.", flush=True)

    total_pending = len(pending)
    if verbose:
        print(f"[INFO] Pending evaluations: {total_pending}", flush=True)

    if total_pending == 0:
        print(f"[DONE] All 600 predictions already cached successfully for {model_id}!", flush=True)
        return 0, 0, 600

    # Run up to batch_size items
    to_run = pending[:batch_size]
    num_new_success = 0
    num_new_fail = 0

    for i, (cache_key, job) in enumerate(to_run):
        done_count = len(done_keys) + 1
        total_done = 600 - total_pending + i + 1

        result = None
        for attempt in range(5):
            try:
                result = judge.evaluate_reply(
                    customer_message=job["gold"]["message"],
                    predicted_intent=job["pred"]["predicted_intent"],
                    predicted_must_escalate=bool(job["pred"]["predicted_must_escalate"]),
                    predicted_reply=job["pred"]["predicted_reply"],
                    gold_must_escalate=bool(job["gold"]["must_escalate"]),
                    prior_context=job["gold"].get("prior_context", ""),
                    retrieved_evidence=job["evidence"],
                )
                break
            except KeyboardInterrupt:
                print("\n[INTERRUPTED] Stopping. Resume by re-running this script.", flush=True)
                print(f"[PROGRESS] Completed {i}/{len(to_run)} in this batch.", flush=True)
                sys.exit(0)
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "rate_limit" in err_str.lower() or "resource_exhausted" in err_str.lower():
                    delay = parse_retry_delay(err_str)
                    delay = max(delay, 3.0)
                    print(f"  [RATE LIMIT] attempt {attempt+1}/5 — waiting {delay:.1f}s...", flush=True)
                    time.sleep(delay)
                else:
                    print(f"  [ERROR] attempt {attempt+1}/5: {err_str[:120]}", flush=True)
                    time.sleep(3.0)

        if result is None:
            if verbose:
                print(f"  [{total_done}/600] FAIL (retries exhausted) {job['ex_id']} [{job['sys_key']}]", flush=True)
            num_new_fail += 1
            continue

        if result.get("llm_failure"):
            num_new_fail += 1
            status = "FAIL"
        else:
            num_new_success += 1
            done_keys.add(cache_key)
            status = "OK"

        from_cache_label = "(cache)" if result.get("from_cache") else "(live)"
        if verbose:
            print(f"  [{total_done}/600] {status} {from_cache_label} {job['ex_id']} [{job['sys_key']}]", flush=True)

        # Delay between live calls
        if not result.get("from_cache") and i < len(to_run) - 1:
            time.sleep(min_delay)

    final_success = len(done_keys)
    print(f"\n[BATCH DONE] New successes: {num_new_success}, New failures: {num_new_fail}", flush=True)
    print(f"[PROGRESS]   Total cached ({model_id}): {final_success}/600", flush=True)
    remaining = 600 - final_success
    if remaining > 0:
        print(f"[NEXT STEP]  {remaining} still pending. Re-run this script to continue.", flush=True)
    else:
        print(f"[COMPLETE]   All 600 predictions cached! Run: python reproduce.py --mode cached-judge", flush=True)

    return num_new_success, num_new_fail, final_success


def main():
    from configs.settings import settings

    parser = argparse.ArgumentParser(description="Batch LLM Judge Runner")
    parser.add_argument("--provider", type=str, default=None,
                        help="LLM provider (groq, gemini, etc.)")
    parser.add_argument("--model", type=str, default=None,
                        help="LLM model name")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Max new API calls per run (default 100)")
    parser.add_argument("--status", action="store_true",
                        help="Show current coverage and exit")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Min seconds between API calls (default 2.0)")
    args = parser.parse_args()

    provider = args.provider or settings.llm_provider
    model = args.model or getattr(settings, "llm_judge_model", "openai/gpt-oss-120b")
    model_id = f"{provider}/{model}"

    suc, fail, total = get_cache_coverage(model_id)
    print(f"=== LLM Judge Batch Runner ===", flush=True)
    print(f"Model: {model_id}", flush=True)
    print(f"Current coverage: {suc} successful / 600 ({100*suc/600:.1f}%)", flush=True)
    print(f"Failed entries in cache: {fail}", flush=True)
    print(f"Total cache entries (all models): {total}", flush=True)
    print(flush=True)

    if args.status:
        return

    run_batch(
        provider=provider,
        model=model,
        batch_size=args.batch_size,
        min_delay=args.delay,
    )


if __name__ == "__main__":
    main()
