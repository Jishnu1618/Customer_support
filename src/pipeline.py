import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.baselines import BaseReplyAgent
from src.retriever import TFIDFRetriever

class MainAgentPipeline(BaseReplyAgent):
    """
    Main Agent Pipeline implementing the 6 discrete stages:
    1. classify()  - Classify intent and extract risk signals
    2. retrieve()  - Top-5 TF-IDF retrieval of historical support exchanges
    3. draft()     - Generate draft response with evidence citation
    4. validate()  - Verify schema, cited ID membership, non-empty, prohibited claims
    5. route()     - Capability rules and evidence check for auto_handle vs escalate
    6. log()       - Structured logging of all intermediate states and metrics
    """
    
    INTENTS = [
        "content_availability",
        "technical_support",
        "account_access",
        "billing_and_payments",
        "subscription_and_plans",
        "platform_and_regional",
        "product_feedback",
        "other_or_ambiguous"
    ]
    
    # Precedence-ordered regex rules
    INTENT_RULES = [
        ("account_access", r"\b(hacked|compromised|password|login|log in|sign in|deleted.*facebook|facebook account|sso|stolen|access my account)\b"),
        ("billing_and_payments", r"\b(charge|charged|billing|payment|credit card|pay|student discount|hulu|grace period|refund|invoice|money|deduct|monthly)\b"),
        ("technical_support", r"\b(bug|glitch|crash|freez|shuffle|download|audio|sound|web app|chrome|app|update|timestamp|gui|offline|play|playing|no help|faqs)\b"),
        ("subscription_and_plans", r"\b(family|invite|duo|student|stream|cut off|cancel|delete my account|address|plan|premium|member)\b"),
        ("content_availability", r"\b(song|album|artist|track|unavailable|missing|removed|release|catalog|licens|not available|remove)\b"),
        ("platform_and_regional", r"\b(sonos|siri|apple watch|uwp|india|iraq|south africa|dubai|country|launch|roam|available in|supported in)\b"),
        ("product_feedback", r"\b(discover weekly|recommend|ad|ads|filter|most played|feature|listeners|meme|idea|suggest|dislike)\b"),
    ]
    
    # Risk signal regex patterns
    SECURITY_PATTERNS = r"\b(hacked|compromised|stolen|deleted.*facebook|facebook|sso|access my account)\b"
    ACCOUNT_ACTION_PATTERNS = r"\b(password|reset|delete.*account|change address|grace period|email address|update my payment)\b"
    BILLING_DISPUTE_PATTERNS = r"\b(charged|unauthorized|refund|dispute|double charge|deduct)\b"
    TROUBLESHOOTING_FAILED_PATTERNS = r"\b(faqs no help|nothing works|already tried|still not working|tried everything|faq|support no help)\b"
    PROHIBITED_CLAIM_PATTERNS = r"\b(guarantee refund|refund issued|account deleted|server outage confirmed|fixed your account)\b"

    def __init__(self, retriever: TFIDFRetriever, system_id: str = "main_agent_v1", retrieval_sim_threshold: float = 0.15):
        self.retriever = retriever
        self.system_id = system_id
        self.retrieval_sim_threshold = retrieval_sim_threshold

    # --- Step 1: classify ---
    def classify(self, message: str, prior_context: str) -> Dict[str, Any]:
        combined_text = f"{prior_context} {message}".lower()
        
        # 1. Intent Classification
        classified_intent = "other_or_ambiguous"
        for intent, pattern in self.INTENT_RULES:
            if re.search(pattern, combined_text, re.IGNORECASE):
                classified_intent = intent
                break
                
        # 2. Risk Signal Extraction
        risk_signals = {
            "account_action": bool(re.search(self.ACCOUNT_ACTION_PATTERNS, combined_text, re.IGNORECASE)),
            "sensitive_security": bool(re.search(self.SECURITY_PATTERNS, combined_text, re.IGNORECASE)),
            "financial_dispute": bool(re.search(self.BILLING_DISPUTE_PATTERNS, combined_text, re.IGNORECASE)),
            "unresolved_ambiguity": classified_intent == "other_or_ambiguous" or len(message.strip()) < 15,
            "previous_troubleshooting_failed": bool(re.search(self.TROUBLESHOOTING_FAILED_PATTERNS, combined_text, re.IGNORECASE)),
            "prohibited_claim_detected": bool(re.search(self.PROHIBITED_CLAIM_PATTERNS, combined_text, re.IGNORECASE))
        }
        
        return {
            "classified_intent": classified_intent,
            "risk_signals": risk_signals
        }

    # --- Step 2: retrieve ---
    def retrieve(self, message: str) -> List[Dict[str, Any]]:
        return self.retriever.retrieve(query_text=message, top_k=5)

    @staticmethod
    def _clean_brand_reply(text: str) -> str:
        """Sanitize historical brand reply text to extract core guidance/advice."""
        if not text:
            return ""
        # Remove customer mentions and placeholders
        t = re.sub(r"@?\[CUSTOMER_[A-Za-z0-9_]+\]", "", text)
        t = re.sub(r"@[A-Za-z0-9_]+", "", t)
        # Remove agent signatures (e.g. /CE, ^AB)
        t = re.sub(r"\s+/[A-Z0-9]{2,4}\b", "", t)
        t = re.sub(r"\s+\^[A-Z0-9]{2,4}\b", "", t)
        # Remove t.co shortlinks
        t = re.sub(r"https?://t\.co/[A-Za-z0-9]+", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        # Clean leading punctuation or stray marks
        t = re.sub(r"^[,\.\-\s]+", "", t)
        return t

    # Substantive claim definitions (name, regex pattern, keywords to check in evidence)
    SUBSTANTIVE_CLAIMS = [
        ("clean_reinstall", r"\b(?:clean\s+)?re-?install(?:ing|ed|ation)?\b", ["reinstall", "re-install", "clean install"]),
        ("cache_clearing", r"\bclear(?:ing)?\s+(?:the\s+)?cache\b|\bcache\b", ["cache", "storage"]),
        ("router_reboot", r"\b(?:router|modem|wi-?fi|network|firewall)\b", ["router", "modem", "wi-fi", "wifi", "network", "connection"]),
        ("device_restart", r"\b(?:restart(?:ing)?|reboot(?:ing)?)\b", ["restart", "reboot", "turn off and on"]),
        ("bluetooth", r"\bbluetooth\b", ["bluetooth"]),
        ("offline_mode", r"\boffline\s+mode\b", ["offline"]),
        ("logout_login", r"\b(?:log|sign)\s*(?:out|off)\b", ["log out", "sign out", "logout", "signout"]),
        ("app_update", r"\b(?:update|updating|latest\s+version)\b", ["update", "latest version"]),
        ("reset_url", r"\bspotify\.com/reset\b", ["reset", "spotify.com/reset"]),
        ("account_url", r"\bspotify\.com/account\b", ["account", "spotify.com/account"]),
        ("licensing", r"\blicensing(?:\s+agreements?)?\b|\brights\s+holders?\b", ["licensing", "rights holders", "labels", "catalog"]),
    ]

    # Contradiction patterns: e.g. evidence explicitly advises against an action
    CONTRADICTION_PATTERNS = {
        "clean_reinstall": [r"\bdo(?:n't|\s+not)\s+re-?install\b", r"\bno\s+need\s+to\s+re-?install\b", r"\bavoid\s+re-?installing\b"],
        "cache_clearing": [r"\bdo(?:n't|\s+not)\s+clear\s+(?:the\s+)?cache\b", r"\bno\s+need\s+to\s+clear\s+cache\b"],
        "device_restart": [r"\bdo(?:n't|\s+not)\s+(?:restart|reboot)\b"],
        "router_reboot": [r"\bdo(?:n't|\s+not)\s+(?:restart|reboot)\s+(?:the\s+)?router\b"],
    }

    # --- Step 3: draft ---
    def draft(self, message: str, prior_context: str, intent: str, risk_signals: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        cited_evidence_ids = []
        clean_evidence_advice = ""
        
        if evidence and evidence[0].get("similarity_score", 0.0) >= self.retrieval_sim_threshold:
            raw_brand_reply = evidence[0].get("brand_reply_text", "")
            cleaned = self._clean_brand_reply(raw_brand_reply)
            if len(cleaned) >= 8:
                clean_evidence_advice = cleaned
                cited_evidence_ids.append(evidence[0]["example_id"])
                
        fallback_templates = {
            "content_availability": "Music and podcast availability on Spotify depends on licensing agreements with rights holders, which can vary by country.",
            "technical_support": "Thanks for reaching out! To help troubleshoot, please let us know your device model, OS version, and if this happens on both Wi-Fi and mobile data.",
            "account_access": "If you're having trouble accessing your account, please visit support.spotify.com or reach out to our team via secure contact form.",
            "billing_and_payments": "For billing details or payment issues, check your account overview at spotify.com/account or contact your payment provider.",
            "subscription_and_plans": "You can manage subscription plans, Family invites, and account settings directly at spotify.com/account.",
            "platform_and_regional": "We are constantly working to expand Spotify availability across devices and regions. Stay tuned for official updates!",
            "product_feedback": "Thank you for sharing your feedback with us! You can also submit and vote on feature ideas on the Spotify Community Ideas board.",
            "other_or_ambiguous": "Thanks for reaching out to Spotify Cares! Let us know how we can assist with your Spotify account or music playback."
        }
        
        if clean_evidence_advice:
            draft_reply = clean_evidence_advice
        else:
            draft_reply = fallback_templates.get(intent, fallback_templates["other_or_ambiguous"])
            
        return {
            "draft_reply": draft_reply,
            "cited_evidence_ids": cited_evidence_ids
        }

    # --- Step 4: validate ---
    def validate(self, draft_output: Dict[str, Any], evidence: List[Dict[str, Any]], intent: str, risk_signals: Dict[str, Any]) -> Dict[str, Any]:
        valid_schema = True
        errors = []
        
        draft_reply = draft_output.get("draft_reply", "")
        cited_ids = draft_output.get("cited_evidence_ids", [])
        retrieved_ids = [e["example_id"] for e in evidence]
        retrieved_evidence_map = {e["example_id"]: e for e in evidence if "example_id" in e}
        
        # 1. Non-empty check
        if not draft_reply or len(draft_reply.strip()) == 0:
            valid_schema = False
            errors.append("empty_reply")
            
        # 2. Allowed intent label check
        if intent not in self.INTENTS:
            valid_schema = False
            errors.append("invalid_intent_label")
            
        # 3. Cited ID membership check
        for cid in cited_ids:
            if cid not in retrieved_ids:
                valid_schema = False
                errors.append(f"invalid_cited_id_{cid}")
                
        # 4. Prohibited claims check (no unverified refunds/outages/account changes)
        if re.search(self.PROHIBITED_CLAIM_PATTERNS, draft_reply, re.IGNORECASE):
            valid_schema = False
            errors.append("prohibited_claim_in_draft")

        # 5. Substantive claim support check
        for claim_name, pattern, support_keywords in self.SUBSTANTIVE_CLAIMS:
            if re.search(pattern, draft_reply, re.IGNORECASE):
                if not cited_ids:
                    # Specific technical troubleshooting action asserted without cited evidence
                    valid_schema = False
                    errors.append(f"unsupported_substantive_claim: '{claim_name}' asserted without cited evidence")
                else:
                    supported = False
                    for cid in cited_ids:
                        ev_item = retrieved_evidence_map.get(cid)
                        if not ev_item:
                            continue
                        ev_brand_text = ev_item.get("brand_reply_text", "")
                        ev_combined_text = (ev_brand_text + " " + ev_item.get("customer_text", "")).lower()
                        
                        # Check for explicit contradiction in evidence
                        contradictions = self.CONTRADICTION_PATTERNS.get(claim_name, [])
                        is_contradicted = any(re.search(cp, ev_combined_text, re.IGNORECASE) for cp in contradictions)
                        if is_contradicted:
                            valid_schema = False
                            errors.append(f"contradictory_evidence_claim: '{claim_name}' is explicitly contradicted by cited evidence {cid}")
                            break
                            
                        # Check if claim is attested in cited evidence
                        if any(kw.lower() in ev_combined_text for kw in support_keywords):
                            supported = True
                            break
                            
                    if not supported and valid_schema:
                        valid_schema = False
                        errors.append(f"unsupported_substantive_claim: '{claim_name}' not supported by cited evidence")
            
        return {
            "is_valid": valid_schema,
            "validation_errors": errors
        }

    # --- Step 5: route ---
    def route(self, intent: str, risk_signals: Dict[str, Any], validation_result: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        must_escalate = False
        reasons = []
        
        # Fixed routing rules:
        # 1. Sensitive security
        if risk_signals.get("sensitive_security"):
            must_escalate = True
            reasons.append("sensitive_security_request")
            
        # 2. Account-specific investigation / action required
        if risk_signals.get("account_action"):
            must_escalate = True
            reasons.append("account_action_required")
            
        # 3. Financial / billing dispute
        if risk_signals.get("financial_dispute"):
            must_escalate = True
            reasons.append("financial_billing_dispute")
            
        # 4. Previous troubleshooting failed
        if risk_signals.get("previous_troubleshooting_failed"):
            must_escalate = True
            reasons.append("previous_troubleshooting_failed")
            
        # 5. Unresolved ambiguity
        if risk_signals.get("unresolved_ambiguity"):
            must_escalate = True
            reasons.append("unresolved_ambiguity")
            
        # 6. Schema/validation failures
        if not validation_result.get("is_valid", True):
            must_escalate = True
            reasons.append("validation_schema_failure")
            
        # 7. Low evidence confidence for complex intents
        top_score = evidence[0]["similarity_score"] if evidence else 0.0
        if intent in ["account_access", "billing_and_payments"] and top_score < self.retrieval_sim_threshold:
            must_escalate = True
            reasons.append("low_retrieval_evidence_confidence")
            
        reason_code = "; ".join(reasons) if reasons else "safe_auto_handle_standard_troubleshooting"
        decision = "escalate" if must_escalate else "auto_handle"
        
        return {
            "must_escalate": must_escalate,
            "decision": decision,
            "reason_code": reason_code
        }

    # --- Step 6: log & main execution interface ---
    def predict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        example_id = record.get("example_id", "")
        message = record.get("message", "")
        prior_context = record.get("prior_context", "")
        
        intermediate_states = {}
        
        try:
            # Stage 1: Classify
            classify_res = self.classify(message, prior_context)
            intermediate_states["classify"] = classify_res
            
            # Stage 2: Retrieve
            retrieve_res = self.retrieve(message)
            intermediate_states["retrieve"] = retrieve_res
            
            # Stage 3: Draft
            draft_res = self.draft(
                message, prior_context,
                classify_res["classified_intent"],
                classify_res["risk_signals"],
                retrieve_res
            )
            intermediate_states["draft"] = draft_res
            
            # Stage 4: Validate
            validate_res = self.validate(
                draft_res, retrieve_res,
                classify_res["classified_intent"],
                classify_res["risk_signals"]
            )
            intermediate_states["validate"] = validate_res
            
            # Stage 5: Route
            route_res = self.route(
                classify_res["classified_intent"],
                classify_res["risk_signals"],
                validate_res,
                retrieve_res
            )
            intermediate_states["route"] = route_res
            
            runtime_ms = (time.perf_counter() - start_time) * 1000.0
            
            # Stage 6: Log & Output Record Assembly
            retrieved_ids = draft_res.get("cited_evidence_ids", [])
            if not retrieved_ids and retrieve_res:
                retrieved_ids = [e["example_id"] for e in retrieve_res[:2]]
                
            output_record = {
                "example_id": example_id,
                "system_id": self.system_id,
                "predicted_intent": classify_res["classified_intent"],
                "predicted_must_escalate": route_res["must_escalate"],
                "predicted_reply": draft_res["draft_reply"],
                "predicted_reason": route_res["reason_code"],
                "retrieved_source_ids": retrieved_ids,
                "runtime_ms": round(runtime_ms, 3),
                "intermediate_states": intermediate_states
            }
            return output_record
            
        except Exception as e:
            # Fallback error handling: preserve error and route to escalation
            runtime_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "example_id": example_id,
                "system_id": self.system_id,
                "predicted_intent": "other_or_ambiguous",
                "predicted_must_escalate": True,
                "predicted_reply": "Thanks for reaching out! We are forwarding your inquiry to a support agent for further review.",
                "predicted_reason": f"pipeline_exception_escalation: {str(e)}",
                "retrieved_source_ids": [],
                "runtime_ms": round(runtime_ms, 3),
                "intermediate_states": {"error": str(e)}
            }
