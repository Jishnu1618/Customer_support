"""
reproduce.py — Reply Agent Reproducibility CLI

Modes:
  offline         Recalculate classification/routing metrics and heuristic reply scores
                  from saved predictions. No API key required. < 5 seconds.
                  NOTE: reply-quality scores are heuristic (keyword/regex), not LLM.

  inference       Run live inference for all 3 systems on the 200 eval records.
                  No API key required (local TF-IDF pipeline).

  cached-judge    Recompute metrics from saved LLM judgments without API calls.
                  Requires results/phase6/llm_judge_cache.jsonl (run llm-judge first).
                  Stale cache entries are rejected, not silently used.
                  DESIGNED FOR REVIEWERS: reproduce headline results within 15 minutes.

  llm-judge       Score all 600 predictions with the LLM judge. Requires API key.
                  Results cached in results/phase6/llm_judge_cache.jsonl.

  test            Run full test suite (pytest).

  all             Run: offline → inference → llm-judge → test.
"""
import sys
import argparse
import subprocess
from pathlib import Path
from evaluate import run_evaluation

ROOT = Path(__file__).parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def get_python_exe() -> str:
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def run_offline():
    print("=== Offline Headline Recalculation Mode ===")
    print("Recalculating classification/routing metrics and heuristic reply scores")
    print("from saved predictions. No API key required.")
    print("NOTE: reply-quality scores are HEURISTIC (keyword/regex), NOT LLM judgments.")
    run_evaluation(use_llm=False, cached_judge=False)
    print("[OK] Headline results successfully recalculated.")


def run_cached_judge():
    print("=== Cached LLM Judge Mode (Offline, No API Calls) ===")
    print("Recomputing metrics from saved LLM judgments.")
    print("This recomputes metrics from results/phase6/llm_judge_cache.jsonl.")
    print("Stale cache entries (when replies/evidence/config changed) are rejected.")
    print("Run 'python reproduce.py --mode llm-judge' first to populate the cache.")
    run_evaluation(use_llm=False, cached_judge=True)
    print("[OK] Cached LLM judge metrics recomputed.")


def run_llm_judge():
    print("=== Live LLM Judge Scoring Mode ===")
    print("Scoring 600 predictions with the LLM judge (groq/compound).")
    print("Results cached in results/phase6/llm_judge_cache.jsonl with provenance.")
    print("Failures recorded. Heuristic scores NOT substituted on failure.")
    run_evaluation(use_llm=True, cached_judge=False)


def run_inference():
    print("=== Live Inference Execution Mode ===")
    print("Running live inference for Baseline 0, Baseline 1, and Main Agent (200 records).")
    py_exe = get_python_exe()
    subprocess.run([py_exe, "-m", "src.run_phase5_eval"], cwd=ROOT, check=True)


def run_tests():
    print("=== Full Project Test Suite Mode ===")
    py_exe = get_python_exe()
    subprocess.run([py_exe, "-m", "pytest"], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Reply Agent Reproducibility CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["offline", "inference", "cached-judge", "llm-judge", "test", "all"],
        default="offline",
        help=(
            "'offline' (heuristic metrics, no API key, < 5s), "
            "'cached-judge' (offline LLM metrics from cache, no API key), "
            "'llm-judge' (live LLM scoring, needs API key), "
            "'inference' (run live models), "
            "'test' (pytest), or 'all'"
        ),
    )
    args = parser.parse_args()

    if args.mode == "offline":
        run_offline()
    elif args.mode == "cached-judge":
        run_cached_judge()
    elif args.mode == "llm-judge":
        run_llm_judge()
    elif args.mode == "inference":
        run_inference()
    elif args.mode == "test":
        run_tests()
    elif args.mode == "all":
        run_offline()
        run_inference()
        run_llm_judge()
        run_tests()


if __name__ == "__main__":
    main()
