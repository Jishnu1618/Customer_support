import time
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseReplyAgent(ABC):
    """
    Abstract Base Class for all Reply Agents / Baseline Models.
    Enforces a unified input interface and prediction output fields.
    """
    
    @abstractmethod
    def predict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict intent, escalation, reply text, and retrieved sources for a single input record.
        
        Input record schema:
          - example_id (str)
          - conversation_id (str)
          - message (str)
          - prior_context (str)
          
        Returns dictionary with fields:
          - example_id (str)
          - system_id (str)
          - predicted_intent (str)
          - predicted_must_escalate (bool)
          - predicted_reply (str)
          - predicted_reason (str)
          - retrieved_source_ids (List[str])
          - runtime_ms (float)
        """
        pass
        
    def predict_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict for a batch of records."""
        return [self.predict(r) for r in records]


class Baseline0MajorityAgent(BaseReplyAgent):
    """
    Baseline 0: Majority Class & Always Escalate.
    - Intent: Most frequent development set intent ('platform_and_regional').
    - Escalation: Always True (escalate).
    - Reply: Generic fixed acknowledgment.
    """
    
    def __init__(self, system_id: str = "baseline_0_majority"):
        self.system_id = system_id
        self.majority_intent = "platform_and_regional"
        self.fixed_reply = (
            "Thanks for reaching out to Spotify Cares! We've forwarded your message "
            "to a support specialist who will review your account details shortly. "
            "Send us a DM if you need anything else."
        )
        
    def predict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        example_id = record.get("example_id", "")
        
        runtime_ms = (time.perf_counter() - start_time) * 1000.0
        
        return {
            "example_id": example_id,
            "system_id": self.system_id,
            "predicted_intent": self.majority_intent,
            "predicted_must_escalate": True,
            "predicted_reply": self.fixed_reply,
            "predicted_reason": "fixed_majority_class_always_escalate",
            "retrieved_source_ids": [],
            "runtime_ms": round(runtime_ms, 3)
        }


class Baseline1RuleAgent(BaseReplyAgent):
    """
    Baseline 1: Keyword Rules, Fixed Templates, & Explicit Escalation Policy.
    - Intent: Regex keyword matching adhering to Phase 3 tie-break precedence.
    - Escalation: Explicit rules for account security, billing disputes, SSO recovery, and account deletion.
    - Reply: Procedural template responses with attached historical Knowledge Base source IDs.
    """
    
    # Precedence order matching Phase 3 tie-breaking
    RULES = [
        (
            "account_access",
            r"\b(hacked|compromised|password|login|log in|sign in|deleted facebook|facebook account|sso|stolen|access my account)\b",
            "KB-003-ACCOUNT-RECOVERY",
            "If you're having trouble logging in or suspect your account was compromised, please reset your password at spotify.com/reset or contact support for account recovery."
        ),
        (
            "billing_and_payments",
            r"\b(charge|charged|billing|payment|credit card|pay|student discount|hulu|grace period|refund|invoice|money|deduct|monthly)\b",
            "KB-004-BILLING-HELP",
            "For billing inquiries and payment updates, check your subscription status and payment methods at spotify.com/account or contact your bank."
        ),
        (
            "technical_support",
            r"\b(bug|glitch|crash|freez|shuffle|download|audio|sound|web app|chrome|app|update|timestamp|gui|offline|play|playing)\b",
            "KB-002-TROUBLESHOOTING",
            "We recommend performing a clean reinstall of the app and clearing cache. If playback issues persist, please reply with your device model and OS version!"
        ),
        (
            "subscription_and_plans",
            r"\b(family|invite|duo|student|stream|cut off|cancel|delete my account|address|plan|premium|member)\b",
            "KB-005-FAMILY-PLANS",
            "You can manage your subscription tier, Family plan member invites, and account settings directly at spotify.com/account."
        ),
        (
            "content_availability",
            r"\b(song|album|artist|track|unavailable|missing|removed|release|catalog|licens|not available|remove)\b",
            "KB-001-LICENSING",
            "Music and podcast availability on Spotify depends on licensing agreements with rights holders, which can vary by region and change over time."
        ),
        (
            "platform_and_regional",
            r"\b(sonos|siri|apple watch|uwp|india|iraq|south africa|dubai|country|launch|roam|available in|supported in)\b",
            "KB-006-REGIONAL-AVAILABILITY",
            "We are constantly working to expand Spotify availability across hardware devices and new regions. Follow our newsroom for official rollout updates!"
        ),
        (
            "product_feedback",
            r"\b(discover weekly|recommend|ad|ads|filter|most played|feature|listeners|meme|idea|suggest|dislike)\b",
            "KB-007-COMMUNITY-FEEDBACK",
            "Thank you for sharing your feedback with us! You can also submit and vote on feature requests on the Spotify Community Ideas board."
        ),
    ]
    
    ESCALATION_REGEX = r"\b(hacked|compromised|stolen|deleted facebook|refund|unauthorized|dispute|grace period|delete my account|hacked account|chargeback)\b"
    
    def __init__(self, system_id: str = "baseline_1_rules"):
        self.system_id = system_id
        
    def predict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        example_id = record.get("example_id", "")
        message = record.get("message", "").lower()
        prior_context = record.get("prior_context", "").lower()
        combined_text = f"{prior_context} {message}"
        
        # 1. Intent Classification via precedence rules
        predicted_intent = "other_or_ambiguous"
        kb_source_id = "KB-008-GENERAL-HELP"
        template_reply = "Thanks for reaching out to Spotify Cares! Let us know how we can assist with your Spotify account or music playback."
        reason = "fallback_keyword_unmatched"
        
        for intent, pattern, source_id, reply_text in self.RULES:
            if re.search(pattern, combined_text, re.IGNORECASE):
                predicted_intent = intent
                kb_source_id = source_id
                template_reply = reply_text
                reason = f"keyword_match_{intent}"
                break
                
        # 2. Escalation Policy
        must_escalate = False
        if re.search(self.ESCALATION_REGEX, combined_text, re.IGNORECASE):
            must_escalate = True
            reason += "_sensitive_escalation_rule"
        elif predicted_intent in ["account_access"]:
            must_escalate = True
            reason += "_account_security_escalation"
            
        runtime_ms = (time.perf_counter() - start_time) * 1000.0
        
        return {
            "example_id": example_id,
            "system_id": self.system_id,
            "predicted_intent": predicted_intent,
            "predicted_must_escalate": must_escalate,
            "predicted_reply": template_reply,
            "predicted_reason": reason,
            "retrieved_source_ids": [kb_source_id],
            "runtime_ms": round(runtime_ms, 3)
        }
