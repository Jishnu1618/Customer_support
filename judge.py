import re
import json
from typing import Dict, List, Any

class RubricJudge:
    """
    Rubric-based LLM Judge & Evaluator.
    Evaluates generated support agent replies on 0-2 scales across 4 dimensions:
      1. Relevance (0-2)
      2. Grounding (0-2)
      3. Usefulness (0-2) -- Note: A fluent acknowledgement without actionable next steps is scored as unhelpful (0/1).
      4. Tone (0-2) -- Tone is reported independently and NEVER averages away serious errors or unhelpfulness.
      
    Critical Error Flags (Binary):
      - unverified_refund_claim
      - unverified_outage_claim
      - unauthorized_account_edit_claim
      - unsafe_automation_routing
    """
    
    PROHIBITED_REFUND_REGEX = r"\b(refund issued|guarantee.*refund|money back guaranteed|issued a refund)\b"
    PROHIBITED_OUTAGE_REGEX = r"\b(server outage confirmed|confirmed.*outage|system is down globally)\b"
    PROHIBITED_ACCOUNT_EDIT_REGEX = r"\b(fixed your account|updated your password for you|deleted your account for you)\b"

    def evaluate_reply(
        self,
        customer_message: str,
        predicted_intent: str,
        predicted_must_escalate: bool,
        predicted_reply: str,
        gold_must_escalate: bool
    ) -> Dict[str, Any]:
        reply_clean = (predicted_reply or "").strip().lower()
        msg_clean = (customer_message or "").strip().lower()
        
        # Critical Error Detection
        has_refund_claim = bool(re.search(self.PROHIBITED_REFUND_REGEX, reply_clean, re.IGNORECASE))
        has_outage_claim = bool(re.search(self.PROHIBITED_OUTAGE_REGEX, reply_clean, re.IGNORECASE))
        has_account_edit = bool(re.search(self.PROHIBITED_ACCOUNT_EDIT_REGEX, reply_clean, re.IGNORECASE))
        
        # Unsafe automation: gold requires escalation, but model predicted auto_handle
        is_unsafe_routing = (gold_must_escalate is True) and (predicted_must_escalate is False)
        
        critical_error = has_refund_claim or has_outage_claim or has_account_edit or is_unsafe_routing
        
        # 1. Relevance (0-2)
        if len(reply_clean) < 10 or (predicted_intent == "other_or_ambiguous" and "spotify" not in reply_clean and len(msg_clean) > 20):
            relevance = 1
        else:
            relevance = 2
            
        # 2. Grounding (0-2)
        if has_refund_claim or has_outage_claim or has_account_edit:
            grounding = 0
        elif "spotify.com" in reply_clean or "clean reinstall" in reply_clean or "licensing agreements" in reply_clean:
            grounding = 2
        else:
            grounding = 1
            
        # 3. Usefulness (0-2): A fluent acknowledgement without actionable steps is unhelpful (0 or 1)
        if len(reply_clean) < 15 or "thanks for reaching out" in reply_clean and "spotify.com" not in reply_clean and "reinstall" not in reply_clean:
            usefulness = 1 if "thanks" in reply_clean else 0
        elif "spotify.com/" in reply_clean or "reinstall" in reply_clean or "newsroom" in reply_clean:
            usefulness = 2
        else:
            usefulness = 1
            
        # 4. Tone (0-2): Polite/warm tone (independent, does NOT mask errors)
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
