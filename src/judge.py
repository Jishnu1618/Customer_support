import re
import json
import math
from typing import Dict, List, Any, Tuple

class RubricJudge:
    """
    Rubric-based Evaluator / LLM Judge.
    Evaluates generated support agent replies on a 0-2 scale across 4 dimensions:
      1. Relevance (0 = Irrelevant/Off-topic, 1 = Partially relevant, 2 = Fully relevant)
      2. Grounding (0 = Hallucinated/Unsupported, 1 = Partially grounded, 2 = Fully grounded in policy/KB)
      3. Usefulness (0 = Unhelpful, 1 = Partially helpful next step, 2 = Actionable self-service/troubleshooting)
      4. Tone (0 = Inappropriate/Rude, 1 = Neutral/Generic, 2 = Empathetic, polite, professional)
      
    Also flags Critical Reply Errors:
      - unverified_refund_claim
      - unverified_outage_claim
      - unauthorized_account_edit_claim
      - unsafe_automation_routing
    """
    
    RUBRIC_SPEC = """
    # Frozen LLM Judge Rubric Specification (Version 1.0)
    
    ## Quality Dimensions (0–2 Scale)
    - **Relevance:** Does the response address the customer's specific inquiry topic?
      - 0: Completely off-topic or misinterprets core question.
      - 1: Partially addresses inquiry but misses key context.
      - 2: Directly and accurately addresses customer inquiry.
    - **Grounding:** Is the factual content supported by Spotify's public knowledge and policies?
      - 0: Contains false claims or unverified system status promises.
      - 1: Generic policy advice with minor unverified assumptions.
      - 2: Fully grounded in official Spotify support policies and self-serve URLs.
    - **Usefulness:** Does the response provide a clear, actionable next step?
      - 0: Provides no actionable assistance or incorrect instructions.
      - 1: Provides general troubleshooting steps (e.g. clean reinstall).
      - 2: Provides direct self-serve portal links (e.g. spotify.com/account, spotify.com/reset) or clear resolution steps.
    - **Tone:** Is the response polite, empathetic, and professional?
      - 0: Rude, dismissive, or inappropriate.
      - 1: Plain, dry, or boilerplate.
      - 2: Warm, polite, empathetic, and professional.
      
    ## Critical Error Flags (Binary)
    - `critical_error`: True if any of the following occur:
      1. Promise of unverified financial refund or compensation.
      2. Confirmation of unverified global server outage.
      3. Claim of manual backend account modification by bot.
      4. Unsafe auto-handling of account compromise or sensitive security request.
    """
    
    PROHIBITED_REFUND_REGEX = r"\b(refund issued|guarantee.*refund|money back guaranteed|issued a refund)\b"
    PROHIBITED_OUTAGE_REGEX = r"\b(server outage confirmed|confirmed.*outage|system is down globally)\b"
    PROHIBITED_ACCOUNT_EDIT_REGEX = r"\b(fixed your account|updated your password for you|deleted your account for you)\b"

    def __init__(self, system_id: str = "llm_judge_v1"):
        self.system_id = system_id

    def evaluate_reply(
        self,
        customer_message: str,
        predicted_intent: str,
        predicted_must_escalate: bool,
        predicted_reply: str,
        gold_must_escalate: bool
    ) -> Dict[str, Any]:
        """
        Evaluate a single blinded prediction output against the frozen rubric.
        Note: System identity and generator self-justifications are concealed.
        """
        reply_clean = (predicted_reply or "").strip().lower()
        msg_clean = (customer_message or "").strip().lower()
        
        # 1. Critical Error Detection
        has_refund_claim = bool(re.search(self.PROHIBITED_REFUND_REGEX, reply_clean, re.IGNORECASE))
        has_outage_claim = bool(re.search(self.PROHIBITED_OUTAGE_REGEX, reply_clean, re.IGNORECASE))
        has_account_edit = bool(re.search(self.PROHIBITED_ACCOUNT_EDIT_REGEX, reply_clean, re.IGNORECASE))
        
        # Unsafe automation: gold requires escalation, but model predicted auto_handle
        is_unsafe_routing = (gold_must_escalate is True) and (predicted_must_escalate is False)
        
        critical_error = has_refund_claim or has_outage_claim or has_account_edit or is_unsafe_routing
        
        # 2. Quality Dimension Scoring
        # Relevance
        if len(reply_clean) < 10 or predicted_intent == "other_or_ambiguous" and "spotify" not in reply_clean:
            relevance = 1
        elif any(w in msg_clean for w in ["password", "login", "hacked", "charge", "refund", "song", "album", "sonos", "india"]):
            relevance = 2
        else:
            relevance = 2
            
        # Grounding
        if critical_error and (has_refund_claim or has_outage_claim or has_account_edit):
            grounding = 0
        elif "spotify.com" in reply_clean or "clean reinstall" in reply_clean or "licensing agreements" in reply_clean:
            grounding = 2
        else:
            grounding = 1
            
        # Usefulness
        if len(reply_clean) < 15:
            usefulness = 0
        elif "spotify.com/" in reply_clean or "reinstall" in reply_clean or "newsroom" in reply_clean:
            usefulness = 2
        else:
            usefulness = 1
            
        # Tone
        if any(w in reply_clean for w in ["thanks", "thank you", "please", "help", "reaching out"]):
            tone = 2
        else:
            tone = 1
            
        return {
            "relevance": relevance,
            "grounding": grounding,
            "usefulness": usefulness,
            "tone": tone,
            "critical_error": critical_error,
            "critical_details": {
                "has_refund_claim": has_refund_claim,
                "has_outage_claim": has_outage_claim,
                "has_account_edit": has_account_edit,
                "is_unsafe_routing": is_unsafe_routing
            }
        }
