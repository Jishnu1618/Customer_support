import time
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.baselines import BaseReplyAgent
from src.retriever import TFIDFRetriever

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional sentence-transformers semantic classifier (lazy-loaded)
# ---------------------------------------------------------------------------
_SEMANTIC_MODEL = None
_SEMANTIC_MODEL_ATTEMPTED = False

def _get_semantic_model():
    """Lazy-load the sentence-transformer model. Returns None if unavailable."""
    global _SEMANTIC_MODEL, _SEMANTIC_MODEL_ATTEMPTED
    if _SEMANTIC_MODEL_ATTEMPTED:
        return _SEMANTIC_MODEL
    _SEMANTIC_MODEL_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        _SEMANTIC_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Semantic classifier loaded: all-MiniLM-L6-v2")
    except Exception as e:
        logger.warning(f"sentence-transformers not available, skipping semantic fallback: {e}")
        _SEMANTIC_MODEL = None
    return _SEMANTIC_MODEL


class MainAgentPipeline(BaseReplyAgent):
    """
    Main Agent Pipeline implementing the 6 discrete stages:
    1. classify()  - Classify intent (regex + semantic fallback) and extract risk signals
    2. retrieve()  - Top-5 TF-IDF retrieval of historical support exchanges
    3. draft()     - Generate structured draft reply with evidence citation
    4. validate()  - Verify schema, cited ID membership, non-empty, prohibited claims
    5. route()     - Capability rules and evidence check for auto_handle vs escalate
    6. log()       - Structured logging of all intermediate states and metrics

    v2 changes (2026-09-22):
    - retrieval_sim_threshold raised from 0.15 → 0.25 (fewer low-quality evidence hits)
    - draft() now uses a structured empathy+action+follow-up formatter
    - classify() adds a sentence-transformer semantic fallback when regex returns
      other_or_ambiguous (requires sentence-transformers package)
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

    # Precedence-ordered regex rules (unchanged from v1)
    INTENT_RULES = [
        ("account_access",        r"\b(hacked|compromised|password|login|log in|sign in|deleted.*facebook|facebook account|sso|stolen|access my account)\b"),
        ("billing_and_payments",  r"\b(charge|charged|billing|payment|credit card|pay|student discount|hulu|grace period|refund|invoice|money|deduct|monthly)\b"),
        ("technical_support",     r"\b(bug|glitch|crash|freez|shuffle|download|audio|sound|web app|chrome|app|update|timestamp|gui|offline|play|playing|no help|faqs)\b"),
        ("subscription_and_plans",r"\b(family|invite|duo|student|stream|cut off|cancel|delete my account|address|plan|premium|member)\b"),
        ("content_availability",  r"\b(song|album|artist|track|unavailable|missing|removed|release|catalog|licens|not available|remove)\b"),
        ("platform_and_regional", r"\b(sonos|siri|apple watch|uwp|india|iraq|south africa|dubai|country|launch|roam|available in|supported in)\b"),
        ("product_feedback",      r"\b(discover weekly|recommend|ad|ads|filter|most played|feature|listeners|meme|idea|suggest|dislike)\b"),
    ]

    # --- Semantic prototype queries for each intent (used by the semantic fallback) ---
    # One representative sentence per intent; cosine similarity to these decides the label.
    INTENT_PROTOTYPES = {
        "content_availability":   "This song or album is missing from Spotify in my country or region",
        "technical_support":      "The Spotify app is crashing, freezing, or not playing music correctly",
        "account_access":         "I cannot log into my account, my password is not working, my account was hacked",
        "billing_and_payments":   "I was incorrectly charged or have a billing question about my subscription payment",
        "subscription_and_plans": "How do I manage my Spotify Premium, Family plan, or cancel my subscription",
        "platform_and_regional":  "Spotify does not work on my Sonos speaker or is not available in my country yet",
        "product_feedback":       "I have a feature request or feedback about how Spotify's recommendations work",
        "other_or_ambiguous":     "I have a general question or something unrelated to the above categories",
    }
    # Confidence threshold: if best semantic score < this, stay with other_or_ambiguous
    SEMANTIC_CONFIDENCE_THRESHOLD = 0.30

    # Risk signal regex patterns (unchanged from v1)
    SECURITY_PATTERNS             = r"\b(hacked|compromised|stolen|deleted.*facebook|facebook|sso|access my account)\b"
    ACCOUNT_ACTION_PATTERNS       = r"\b(password|reset|delete.*account|change address|grace period|email address|update my payment)\b"
    BILLING_DISPUTE_PATTERNS      = r"\b(charged|unauthorized|refund|dispute|double charge|deduct)\b"
    TROUBLESHOOTING_FAILED_PATTERNS = r"\b(faqs no help|nothing works|already tried|still not working|tried everything|faq|support no help)\b"
    PROHIBITED_CLAIM_PATTERNS     = r"\b(guarantee refund|refund issued|account deleted|server outage confirmed|fixed your account)\b"

    def __init__(
        self,
        retriever: TFIDFRetriever,
        system_id: str = "main_agent_v1",
        retrieval_sim_threshold: float = 0.25,   # ← raised from 0.15
        use_semantic_fallback: bool = True,
    ):
        self.retriever = retriever
        self.system_id = system_id
        self.retrieval_sim_threshold = retrieval_sim_threshold
        self.use_semantic_fallback = use_semantic_fallback

        # Pre-encode intent prototypes if semantic model is available
        self._prototype_embeddings: Optional[Dict[str, Any]] = None
        if self.use_semantic_fallback:
            self._init_semantic_prototypes()

    def _init_semantic_prototypes(self):
        """Pre-encode all intent prototype sentences."""
        model = _get_semantic_model()
        if model is None:
            return
        try:
            import numpy as np
            labels = list(self.INTENT_PROTOTYPES.keys())
            sentences = [self.INTENT_PROTOTYPES[lbl] for lbl in labels]
            embeddings = model.encode(sentences, normalize_embeddings=True)
            self._prototype_embeddings = {
                "labels": labels,
                "embeddings": embeddings,  # shape (n_intents, dim)
            }
            logger.info("Intent prototype embeddings pre-computed.")
        except Exception as e:
            logger.warning(f"Failed to pre-compute prototype embeddings: {e}")
            self._prototype_embeddings = None

    def _semantic_classify(self, text: str) -> Optional[str]:
        """
        Run semantic similarity against intent prototypes.
        Returns the best-matching intent label, or None if confidence is too low
        or the model is unavailable.
        """
        if not self.use_semantic_fallback or self._prototype_embeddings is None:
            return None
        model = _get_semantic_model()
        if model is None:
            return None
        try:
            import numpy as np
            query_emb = model.encode([text], normalize_embeddings=True)[0]  # (dim,)
            prototype_embs = self._prototype_embeddings["embeddings"]       # (n, dim)
            labels = self._prototype_embeddings["labels"]
            # Cosine similarities (embeddings are unit-normalized)
            sims = prototype_embs @ query_emb                               # (n,)
            best_idx = int(np.argmax(sims))
            best_score = float(sims[best_idx])
            best_label = labels[best_idx]
            logger.debug(f"Semantic best: {best_label} (score={best_score:.3f})")
            if best_score >= self.SEMANTIC_CONFIDENCE_THRESHOLD:
                return best_label
            return None
        except Exception as e:
            logger.warning(f"Semantic classification failed: {e}")
            return None

    # --- Step 1: classify ---
    def classify(self, message: str, prior_context: str) -> Dict[str, Any]:
        combined_text = f"{prior_context} {message}".lower()

        # 1a. Regex-based intent classification (primary, precedence-ordered)
        classified_intent = "other_or_ambiguous"
        used_semantic = False
        for intent, pattern in self.INTENT_RULES:
            if re.search(pattern, combined_text, re.IGNORECASE):
                classified_intent = intent
                break

        # 1b. Semantic fallback: if regex fell through to other_or_ambiguous,
        #     try the sentence-transformer to rescue misclassified short/noisy tweets
        if classified_intent == "other_or_ambiguous":
            semantic_intent = self._semantic_classify(f"{prior_context} {message}")
            if semantic_intent and semantic_intent != "other_or_ambiguous":
                classified_intent = semantic_intent
                used_semantic = True
                logger.debug(f"Semantic fallback upgraded intent to: {classified_intent}")

        # 2. Risk signal extraction (unchanged)
        risk_signals = {
            "account_action":                bool(re.search(self.ACCOUNT_ACTION_PATTERNS,         combined_text, re.IGNORECASE)),
            "sensitive_security":            bool(re.search(self.SECURITY_PATTERNS,               combined_text, re.IGNORECASE)),
            "financial_dispute":             bool(re.search(self.BILLING_DISPUTE_PATTERNS,        combined_text, re.IGNORECASE)),
            "unresolved_ambiguity":          classified_intent == "other_or_ambiguous" or len(message.strip()) < 15,
            "previous_troubleshooting_failed": bool(re.search(self.TROUBLESHOOTING_FAILED_PATTERNS, combined_text, re.IGNORECASE)),
            "prohibited_claim_detected":     bool(re.search(self.PROHIBITED_CLAIM_PATTERNS,      combined_text, re.IGNORECASE)),
        }

        return {
            "classified_intent": classified_intent,
            "risk_signals": risk_signals,
            "used_semantic_fallback": used_semantic,
        }

    # --- Step 2: retrieve ---
    def retrieve(self, message: str) -> List[Dict[str, Any]]:
        return self.retriever.retrieve(query_text=message, top_k=5)

    @staticmethod
    def _clean_brand_reply(text: str) -> str:
        """Sanitize historical brand reply text to extract core guidance/advice."""
        if not text:
            return ""
        t = re.sub(r"@?\[CUSTOMER_[A-Za-z0-9_]+\]", "", text)
        t = re.sub(r"@[A-Za-z0-9_]+", "", t)
        t = re.sub(r"\s+/[A-Z0-9]{2,4}\b", "", t)
        t = re.sub(r"\s+\^[A-Z0-9]{2,4}\b", "", t)
        t = re.sub(r"https?://t\.co/[A-Za-z0-9]+", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"^[,\.\-\s]+", "", t)
        return t

    # --- Structured reply formatter ---
    # Intent-specific openers (empathy line), action phrases, and closers
    _OPENERS = {
        "content_availability":   "We're sorry to hear that content isn't showing up for you!",
        "technical_support":      "We're sorry you're experiencing this issue!",
        "account_access":         "We understand how stressful account issues can be.",
        "billing_and_payments":   "We're sorry about the billing concern.",
        "subscription_and_plans": "Happy to help you sort out your subscription.",
        "platform_and_regional":  "Thanks for flagging this platform or availability question.",
        "product_feedback":       "Thanks so much for sharing your thoughts with us!",
        "other_or_ambiguous":     "Thanks for reaching out to Spotify Cares!",
    }
    _CLOSERS = {
        "content_availability":   "If the issue persists, let us know the track/album and your country!",
        "technical_support":      "Reply with your device and OS version if the issue continues — we're here!",
        "account_access":         "DM us if you need further help — your account security is our priority.",
        "billing_and_payments":   "Let us know if you have any other questions about your billing.",
        "subscription_and_plans": "Let us know if there's anything else we can help with!",
        "platform_and_regional":  "Follow our newsroom for the latest rollout updates!",
        "product_feedback":       "Your feedback makes Spotify better — thank you!",
        "other_or_ambiguous":     "Let us know how we can help further!",
    }
    _FALLBACK_ACTIONS = {
        "content_availability":   "Music availability depends on licensing agreements with rights holders, which vary by region and can change over time.",
        "technical_support":      "To troubleshoot, please try: (1) logging out and back in, (2) clearing the cache in your app settings, and (3) reinstalling if the issue persists.",
        "account_access":         "To recover account access, visit spotify.com/reset to reset your password, or use our secure contact form at support.spotify.com.",
        "billing_and_payments":   "You can review your billing details and update payment methods at spotify.com/account.",
        "subscription_and_plans": "You can manage subscription plans, Family invites, and account settings at spotify.com/account.",
        "platform_and_regional":  "We're constantly working to expand Spotify across devices and regions — stay tuned for official updates!",
        "product_feedback":       "You can also submit and vote on feature ideas on the Spotify Community Ideas board at community.spotify.com.",
        "other_or_ambiguous":     "Let us know more about your issue and we'll do our best to point you in the right direction.",
    }

    def _format_reply(self, intent: str, core_advice: str) -> str:
        """
        Wrap core_advice in a consistent empathy → action → follow-up structure.
        If core_advice is empty/too short, use the intent-specific fallback action.
        """
        opener = self._OPENERS.get(intent, self._OPENERS["other_or_ambiguous"])
        closer = self._CLOSERS.get(intent, self._CLOSERS["other_or_ambiguous"])

        if core_advice and len(core_advice.strip()) >= 20:
            action = core_advice.strip()
            # Ensure it ends with a period
            if action and action[-1] not in ".!?":
                action += "."
        else:
            action = self._FALLBACK_ACTIONS.get(intent, self._FALLBACK_ACTIONS["other_or_ambiguous"])

        return f"{opener} {action} {closer}"

    # Substantive claim definitions (unchanged from v1)
    SUBSTANTIVE_CLAIMS = [
        ("clean_reinstall",   r"\b(?:clean\s+)?re-?install(?:ing|ed|ation)?\b",            ["reinstall", "re-install", "clean install"]),
        ("cache_clearing",    r"\bclear(?:ing)?\s+(?:the\s+)?cache\b|\bcache\b",           ["cache", "storage"]),
        ("router_reboot",     r"\b(?:router|modem|wi-?fi|network|firewall)\b",             ["router", "modem", "wi-fi", "wifi", "network", "connection"]),
        ("device_restart",    r"\b(?:restart(?:ing)?|reboot(?:ing)?)\b",                   ["restart", "reboot", "turn off and on"]),
        ("bluetooth",         r"\bbluetooth\b",                                            ["bluetooth"]),
        ("offline_mode",      r"\boffline\s+mode\b",                                      ["offline"]),
        ("logout_login",      r"\b(?:log|sign)\s*(?:out|off)\b",                          ["log out", "sign out", "logout", "signout"]),
        ("app_update",        r"\b(?:update|updating|latest\s+version)\b",                 ["update", "latest version"]),
        ("reset_url",         r"\bspotify\.com/reset\b",                                  ["reset", "spotify.com/reset"]),
        ("account_url",       r"\bspotify\.com/account\b",                                ["account", "spotify.com/account"]),
        ("licensing",         r"\blicensing(?:\s+agreements?)?\b|\brights\s+holders?\b",  ["licensing", "rights holders", "labels", "catalog"]),
    ]

    CONTRADICTION_PATTERNS = {
        "clean_reinstall":  [r"\bdo(?:n't|\s+not)\s+re-?install\b", r"\bno\s+need\s+to\s+re-?install\b", r"\bavoid\s+re-?installing\b"],
        "cache_clearing":   [r"\bdo(?:n't|\s+not)\s+clear\s+(?:the\s+)?cache\b", r"\bno\s+need\s+to\s+clear\s+cache\b"],
        "device_restart":   [r"\bdo(?:n't|\s+not)\s+(?:restart|reboot)\b"],
        "router_reboot":    [r"\bdo(?:n't|\s+not)\s+(?:restart|reboot)\s+(?:the\s+)?router\b"],
    }

    # --- Step 3: draft ---
    def draft(
        self,
        message: str,
        prior_context: str,
        intent: str,
        risk_signals: Dict[str, Any],
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        cited_evidence_ids = []
        core_advice = ""

        # Only use evidence if it meets the raised confidence threshold (0.25)
        if evidence and evidence[0].get("similarity_score", 0.0) >= self.retrieval_sim_threshold:
            raw_brand_reply = evidence[0].get("brand_reply_text", "")
            cleaned = self._clean_brand_reply(raw_brand_reply)
            if len(cleaned) >= 15:          # slightly raised from 8 for quality
                core_advice = cleaned
                cited_evidence_ids.append(evidence[0]["example_id"])

        # Format: empathy opener + core advice/fallback + closer
        draft_reply = self._format_reply(intent, core_advice)

        return {
            "draft_reply": draft_reply,
            "cited_evidence_ids": cited_evidence_ids,
        }

    # --- Step 4: validate ---
    def validate(
        self,
        draft_output: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        intent: str,
        risk_signals: Dict[str, Any],
    ) -> Dict[str, Any]:
        valid_schema = True
        errors = []

        draft_reply = draft_output.get("draft_reply", "")
        cited_ids   = draft_output.get("cited_evidence_ids", [])
        retrieved_ids        = [e["example_id"] for e in evidence]
        retrieved_evidence_map = {e["example_id"]: e for e in evidence if "example_id" in e}

        # 1. Non-empty
        if not draft_reply or len(draft_reply.strip()) == 0:
            valid_schema = False
            errors.append("empty_reply")

        # 2. Allowed intent label
        if intent not in self.INTENTS:
            valid_schema = False
            errors.append("invalid_intent_label")

        # 3. Cited ID membership
        for cid in cited_ids:
            if cid not in retrieved_ids:
                valid_schema = False
                errors.append(f"invalid_cited_id_{cid}")

        # 4. Prohibited claims in draft
        if re.search(self.PROHIBITED_CLAIM_PATTERNS, draft_reply, re.IGNORECASE):
            valid_schema = False
            errors.append("prohibited_claim_in_draft")

        # 5. Substantive claim support check
        for claim_name, pattern, support_keywords in self.SUBSTANTIVE_CLAIMS:
            if re.search(pattern, draft_reply, re.IGNORECASE):
                if not cited_ids:
                    valid_schema = False
                    errors.append(f"unsupported_substantive_claim: '{claim_name}' asserted without cited evidence")
                else:
                    supported = False
                    for cid in cited_ids:
                        ev_item = retrieved_evidence_map.get(cid)
                        if not ev_item:
                            continue
                        ev_brand_text    = ev_item.get("brand_reply_text", "")
                        ev_combined_text = (ev_brand_text + " " + ev_item.get("customer_text", "")).lower()

                        contradictions  = self.CONTRADICTION_PATTERNS.get(claim_name, [])
                        is_contradicted = any(re.search(cp, ev_combined_text, re.IGNORECASE) for cp in contradictions)
                        if is_contradicted:
                            valid_schema = False
                            errors.append(f"contradictory_evidence_claim: '{claim_name}' is explicitly contradicted by cited evidence {cid}")
                            break
                        if any(kw.lower() in ev_combined_text for kw in support_keywords):
                            supported = True
                            break
                    if not supported and valid_schema:
                        valid_schema = False
                        errors.append(f"unsupported_substantive_claim: '{claim_name}' not supported by cited evidence")

        return {
            "is_valid": valid_schema,
            "validation_errors": errors,
        }

    # --- Step 5: route ---
    def route(
        self,
        intent: str,
        risk_signals: Dict[str, Any],
        validation_result: Dict[str, Any],
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        must_escalate = False
        reasons = []

        if risk_signals.get("sensitive_security"):
            must_escalate = True
            reasons.append("sensitive_security_request")

        if risk_signals.get("account_action"):
            must_escalate = True
            reasons.append("account_action_required")

        if risk_signals.get("financial_dispute"):
            must_escalate = True
            reasons.append("financial_billing_dispute")

        if risk_signals.get("previous_troubleshooting_failed"):
            must_escalate = True
            reasons.append("previous_troubleshooting_failed")

        if risk_signals.get("unresolved_ambiguity"):
            must_escalate = True
            reasons.append("unresolved_ambiguity")

        if not validation_result.get("is_valid", True):
            must_escalate = True
            reasons.append("validation_schema_failure")

        # Low evidence confidence for sensitive intents
        top_score = evidence[0]["similarity_score"] if evidence else 0.0
        if intent in ["account_access", "billing_and_payments"] and top_score < self.retrieval_sim_threshold:
            must_escalate = True
            reasons.append("low_retrieval_evidence_confidence")

        reason_code = "; ".join(reasons) if reasons else "safe_auto_handle_standard_troubleshooting"
        decision    = "escalate" if must_escalate else "auto_handle"

        return {
            "must_escalate": must_escalate,
            "decision": decision,
            "reason_code": reason_code,
        }

    # --- Step 6: log & main execution interface ---
    def predict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()

        example_id    = record.get("example_id", "")
        message       = record.get("message", "")
        prior_context = record.get("prior_context", "")

        intermediate_states: Dict[str, Any] = {}

        try:
            classify_res = self.classify(message, prior_context)
            intermediate_states["classify"] = classify_res

            retrieve_res = self.retrieve(message)
            intermediate_states["retrieve"] = retrieve_res

            draft_res = self.draft(
                message, prior_context,
                classify_res["classified_intent"],
                classify_res["risk_signals"],
                retrieve_res,
            )
            intermediate_states["draft"] = draft_res

            validate_res = self.validate(
                draft_res, retrieve_res,
                classify_res["classified_intent"],
                classify_res["risk_signals"],
            )
            intermediate_states["validate"] = validate_res

            route_res = self.route(
                classify_res["classified_intent"],
                classify_res["risk_signals"],
                validate_res,
                retrieve_res,
            )
            intermediate_states["route"] = route_res

            runtime_ms = (time.perf_counter() - start_time) * 1000.0

            retrieved_ids = draft_res.get("cited_evidence_ids", [])
            if not retrieved_ids and retrieve_res:
                retrieved_ids = [e["example_id"] for e in retrieve_res[:2]]

            return {
                "example_id":             example_id,
                "system_id":              self.system_id,
                "predicted_intent":       classify_res["classified_intent"],
                "predicted_must_escalate": route_res["must_escalate"],
                "predicted_reply":        draft_res["draft_reply"],
                "predicted_reason":       route_res["reason_code"],
                "retrieved_source_ids":   retrieved_ids,
                "runtime_ms":             round(runtime_ms, 3),
                "intermediate_states":    intermediate_states,
            }

        except Exception as e:
            runtime_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Pipeline exception for {example_id}: {e}", exc_info=True)
            return {
                "example_id":             example_id,
                "system_id":              self.system_id,
                "predicted_intent":       "other_or_ambiguous",
                "predicted_must_escalate": True,
                "predicted_reply":        "Thanks for reaching out! We are forwarding your inquiry to a support agent for further review.",
                "predicted_reason":       f"pipeline_exception_escalation: {str(e)}",
                "retrieved_source_ids":   [],
                "runtime_ms":             round(runtime_ms, 3),
                "intermediate_states":    {"error": str(e)},
            }
