#!/usr/bin/env python3
"""
demo.py — Interactive & CLI Demonstration of the Spotify Customer Support AI Agent.

This script demonstrates the 6-stage end-to-end agent pipeline:
1. Intent Classification: Classifies incoming customer tweets into one of 8 intents
2. Risk Signal Extraction: Detects security risks, account actions, and billing disputes
3. Historical Evidence Retrieval: Top-K TF-IDF retrieval from 3,000 Spotify support cases
4. Grounded Reply Drafting: Generates reply grounded in retrieved historical resolutions
5. Safety Validation: Checks for prohibited claims and evidence citation integrity
6. Routing Decision: Auto-handle vs. Escalate to human with explicit stated reason

Usage:
    python demo.py --sample       # Run automated demo on 3 diverse customer scenarios
    python demo.py                # Run interactive prompt (type your own tweet)
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.retriever import TFIDFRetriever
from src.pipeline import MainAgentPipeline

KNOWLEDGE_PATH = ROOT / "data" / "processed" / "v2" / "spotify_knowledge.jsonl"

SAMPLE_QUERIES = [
    {
        "title": "Scenario 1: Critical Account Security (Must Escalate)",
        "message": "@SpotifyCares Someone hacked my account, changed the email to a Russian address, and upgraded to family plan!! Please help lock it immediately!",
        "expected_intent": "account_access",
        "expected_routing": "ESCALATE (sensitive_security_request / account_action_required)",
    },
    {
        "title": "Scenario 2: Technical Troubleshooting (Safe Auto-Handle)",
        "message": "@SpotifyCares The app keeps crashing every time I try to play a downloaded song on my iPhone after the new update. What should I do?",
        "expected_intent": "technical_support",
        "expected_routing": "AUTO-HANDLE (safe_auto_handle_standard_troubleshooting)",
    },
    {
        "title": "Scenario 3: Subscription & Billing Inquiry (Auto-Handle / Self-Serve)",
        "message": "@SpotifyCares How do I cancel my Premium subscription before the next billing cycle? Will I lose my saved playlists?",
        "expected_intent": "subscription_and_plans",
        "expected_routing": "AUTO-HANDLE (policy guidance)",
    },
]


def print_separator(char="=", length=75):
    print(char * length)


def run_agent_pipeline(agent: MainAgentPipeline, message: str, title: str = None):
    if title:
        print_separator("=")
        print(f" {title.upper()}")
        print_separator("=")

    print(f"\n[INCOMING TWEET]:\n  \"{message}\"\n")

    res = agent.predict({
        "example_id": "DEMO-LIVE",
        "message": message,
        "prior_context": ""
    })

    print("--- [AGENT PROCESSING PIPELINE] ---")
    print(f" 1. INTENT CLASSIFIED     : {res['predicted_intent'].upper()}")
    
    routing_label = "ESCALATE TO HUMAN" if res["predicted_must_escalate"] else "AUTO-HANDLE"
    print(f" 2. ROUTING DECISION      : {routing_label}")
    print(f"    STATED REASON         : {res['predicted_reason']}")

    citations = res.get("retrieved_source_ids", [])
    print(f" 3. RETRIEVED EVIDENCE    : {len(citations)} historical resolution(s) cited: {citations}")

    print(f"\n 4. DRAFTED REPLY:\n  \"{res['predicted_reply']}\"\n")
    print(f"    Execution Runtime: {res.get('runtime_ms', 0):.2f} ms")
    print_separator("-")


def run_sample_demo(agent: MainAgentPipeline):
    print_separator("=")
    print(" SPOTIFY SUPPORT AI AGENT — LIVE DEMONSTRATION")
    print(" System: main_agent_v1 | Brand: @SpotifyCares")
    print_separator("=")

    for sample in SAMPLE_QUERIES:
        run_agent_pipeline(agent, sample["message"], sample["title"])


def run_interactive(agent: MainAgentPipeline):
    print_separator("=")
    print(" SPOTIFY SUPPORT AI AGENT — INTERACTIVE MODE")
    print(" System: main_agent_v1 | Brand: @SpotifyCares")
    print(" Type your customer support inquiry below (or 'exit' to quit):")
    print_separator("=")

    while True:
        try:
            print("\nEnter customer message:")
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Exiting demo. Goodbye!")
                break

            run_agent_pipeline(agent, user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting demo.")
            break


def main():
    parser = argparse.ArgumentParser(description="Spotify Support AI Agent Demonstration")
    parser.add_argument("--sample", action="store_true", help="Run automated samples instead of interactive prompt")
    args = parser.parse_args()

    if not KNOWLEDGE_PATH.exists():
        print(f"[ERROR] Knowledge base not found at: {KNOWLEDGE_PATH}")
        sys.exit(1)

    print("Initializing TF-IDF Knowledge Retriever and Main Agent Pipeline...")
    retriever = TFIDFRetriever(knowledge_path=KNOWLEDGE_PATH)
    agent = MainAgentPipeline(retriever=retriever)
    print("Initialization complete!\n")

    if args.sample:
        run_sample_demo(agent)
    else:
        if sys.stdin.isatty():
            run_interactive(agent)
        else:
            run_sample_demo(agent)


if __name__ == "__main__":
    main()
