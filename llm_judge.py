"""
LLM-Based Rubric Judge (llm_judge.py)
Version: 2.0
Frozen rubric: results/phase6/judge_rubric.md
Prompt v1 (frozen): prompts/llm_judge_prompt.txt
Prompt v2 (few-shot calibrated): prompts/llm_judge_prompt_v2.txt

Design principles:
  - Every LLM call is cached with full provenance metadata.
  - Cache entries are invalidated when reply, evidence, rubric, model, or prompt change.
  - On LLM failure: record the failure, report coverage gap — NEVER silently substitute heuristic scores.
  - Heuristic judge (judge.py) remains a completely separate, labeled baseline.
  - v2.0 uses few-shot calibration examples per dimension to improve human-judge κ.
    v1 cache entries are preserved (different cache key due to different prompt SHA-256).
"""

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).parent
RUBRIC_PATH = ROOT / "results" / "phase6" / "judge_rubric.md"
PROMPT_PATH_V1 = ROOT / "prompts" / "llm_judge_prompt.txt"
PROMPT_PATH_V2 = ROOT / "prompts" / "llm_judge_prompt_v2.txt"
PROMPT_PATH = PROMPT_PATH_V2   # default to v2 for new runs
CACHE_PATH = ROOT / "results" / "phase6" / "llm_judge_cache.jsonl"

PROMPT_VERSION = "v2.0"   # updated; v1.0 cache preserved via different SHA-256 key
TEMPERATURE = 0.0
MAX_TOKENS = 1024


def _defaults_from_settings():
    """Read provider/model defaults from settings (respects .env)."""
    try:
        from configs.settings import settings
        provider = settings.llm_provider or "groq"
        model = getattr(settings, "llm_judge_model", None) or settings.llm_model or "compound"
        return provider, model
    except Exception:
        return "groq", "compound"


_PROVIDER_DEFAULT, _MODEL_DEFAULT = _defaults_from_settings()
MODEL_DEFAULT = _MODEL_DEFAULT
PROVIDER_DEFAULT = _PROVIDER_DEFAULT


def _parse_retry_delay(error_str: str, default: float = 10.0) -> float:
    """Extract retryDelay seconds from Groq, Gemini, or OpenAI 429 error response."""
    err = str(error_str)
    # Groq format: "Please try again in 4m3.21s" or "try again in 3.75s"
    groq_match = re.search(r"try again in\s+(?:(\d+)m)?(\d+(?:\.\d+)?)s", err, re.IGNORECASE)
    if groq_match:
        mins = float(groq_match.group(1)) if groq_match.group(1) else 0.0
        secs = float(groq_match.group(2))
        return mins * 60.0 + secs + 2.0
    # Gemini format: retryDelay: 60s
    match = re.search(r'retryDelay[^:]*:[^0-9]*([0-9]+)s', err)
    if match:
        return float(match.group(1)) + 1.0
    return default


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _make_cache_key(
    customer_message: str,
    prior_context: str,
    retrieved_evidence: str,
    routing_decision: str,
    predicted_reply: str,
    model_id: str,
    rubric_sha256: str,
    prompt_sha256: str,
) -> str:
    """Deterministic cache key. Any change to inputs or config produces a different key."""
    payload = json.dumps({
        "customer_message": customer_message,
        "prior_context": prior_context,
        "retrieved_evidence": retrieved_evidence,
        "routing_decision": routing_decision,
        "predicted_reply": predicted_reply,
        "model_id": model_id,
        "rubric_sha256": rubric_sha256,
        "prompt_sha256": prompt_sha256,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "prompt_version": PROMPT_VERSION,
    }, sort_keys=True)
    return _sha256(payload)


def _load_cache(cache_path: Path) -> Dict[str, Dict]:
    """Load existing cache entries keyed by cache_key."""
    cache = {}
    if not cache_path.exists():
        return cache
    with open(cache_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ck = entry.get("cache_key")
                if ck:
                    cache[ck] = entry
            except json.JSONDecodeError:
                continue
    return cache


def _append_to_cache(cache_path: Path, entry: Dict) -> None:
    """Append a single entry to the JSONL cache."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _parse_llm_response(raw_text: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Parse LLM JSON response. Returns (parsed_dict, error_message).
    Accepts optional surrounding whitespace/text; extracts first {...} block.
    """
    raw = (raw_text or "").strip()
    # Try direct parse
    try:
        return json.loads(raw), None
    except json.JSONDecodeError:
        pass
    # Try extracting first JSON object
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0)), None
        except json.JSONDecodeError:
            pass
    return None, f"Failed to parse JSON from response: {raw[:300]!r}"


def _validate_schema(parsed: Dict) -> Tuple[bool, Optional[str]]:
    """Validate that the parsed response has all required fields with correct types."""
    required_int_fields = ["relevance", "grounding", "usefulness", "tone"]
    for field in required_int_fields:
        if field not in parsed:
            return False, f"Missing field: {field}"
        val = parsed[field]
        if not isinstance(val, int) or val not in (0, 1, 2):
            return False, f"Field '{field}' must be integer 0/1/2, got {val!r}"
    if "critical_error" not in parsed:
        return False, "Missing field: critical_error"
    if not isinstance(parsed["critical_error"], bool):
        return False, f"Field 'critical_error' must be bool, got {type(parsed['critical_error'])}"
    if "critical_error_details" not in parsed or not isinstance(parsed["critical_error_details"], dict):
        return False, "Missing or invalid 'critical_error_details'"
    return True, None


class LLMRubricJudge:
    """
    LLM-based judge. Evaluates (customer_message, draft_reply, evidence) triples
    against the frozen rubric. Results are cached with full provenance.

    Key invariants:
    - NEVER silently substitutes heuristic scores on LLM failure.
    - Cache entries are rejected when rubric, prompt, model, or inputs change.
    - judge_type is always "llm" on success; failures are recorded explicitly.
    """

    PROMPT_VERSION = PROMPT_VERSION

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        cache_path: Optional[Path] = None,
        use_v2_prompt: bool = True,   # ← v2 (few-shot calibrated) by default
    ):
        from configs.settings import settings
        self.provider = provider or settings.llm_provider
        self.model = model or getattr(settings, "llm_judge_model", MODEL_DEFAULT)
        self.model_id = f"{self.provider}/{self.model}"
        self.cache_path = cache_path or CACHE_PATH

        # Select prompt version
        self.use_v2_prompt = use_v2_prompt
        active_prompt_path = PROMPT_PATH_V2 if use_v2_prompt else PROMPT_PATH_V1
        self.PROMPT_VERSION = "v2.0" if use_v2_prompt else "v1.0"

        # Load frozen artifacts and compute hashes
        if not RUBRIC_PATH.exists():
            raise FileNotFoundError(f"Rubric not found: {RUBRIC_PATH}")
        if not active_prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {active_prompt_path}")

        self.rubric_text = _load_text(RUBRIC_PATH)
        self.prompt_template = _load_text(active_prompt_path)
        self.rubric_sha256 = _sha256(self.rubric_text)
        self.prompt_sha256 = _sha256(self.prompt_template)

        # Load cache
        self._cache: Dict[str, Dict] = _load_cache(self.cache_path)

        # Lazy LLM client
        self._llm_client = None

    def _get_llm_client(self):
        if self._llm_client is None:
            from src.llm import LLMClient
            self._llm_client = LLMClient(provider=self.provider, model=self.model)
        return self._llm_client

    def _build_prompt(
        self,
        customer_message: str,
        prior_context: str,
        retrieved_evidence: str,
        routing_decision: str,
        predicted_reply: str,
    ) -> str:
        return (
            self.prompt_template
            .replace("{customer_message}", customer_message or "(none)")
            .replace("{prior_context}", prior_context or "(none)")
            .replace("{retrieved_evidence}", retrieved_evidence or "(none)")
            .replace("{routing_decision}", routing_decision or "(unknown)")
            .replace("{predicted_reply}", predicted_reply or "(empty)")
        )

    def evaluate_reply(
        self,
        customer_message: str,
        predicted_intent: str,
        predicted_must_escalate: bool,
        predicted_reply: str,
        gold_must_escalate: bool,
        prior_context: str = "",
        retrieved_evidence: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate a single reply. Returns a result dict always containing:
          judge_type, model_id, prompt_version, rubric_sha256, cache_key,
          relevance, grounding, usefulness, tone, critical_error, critical_details,
          + on success: raw_llm_response, rationales, from_cache
          + on failure: llm_failure=True, failure_reason=<str>
        """
        routing_decision = "escalate" if predicted_must_escalate else "auto_handle"

        cache_key = _make_cache_key(
            customer_message=customer_message,
            prior_context=prior_context,
            retrieved_evidence=retrieved_evidence,
            routing_decision=routing_decision,
            predicted_reply=predicted_reply,
            model_id=self.model_id,
            rubric_sha256=self.rubric_sha256,
            prompt_sha256=self.prompt_sha256,
        )

        # Provenance metadata always included in the output
        provenance = {
            "judge_type": "llm",
            "model_id": self.model_id,
            "prompt_version": self.PROMPT_VERSION,
            "rubric_sha256": self.rubric_sha256,
            "cache_key": cache_key,
            "generation_settings": {
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
            },
        }

        # Cache hit (only use successful calls; retry failures)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if not cached.get("llm_failure"):
                result = {**provenance, **cached.get("scores", {}), "from_cache": True}
                return result

        # Cache miss — call LLM with retry
        prompt_text = self._build_prompt(
            customer_message=customer_message,
            prior_context=prior_context,
            retrieved_evidence=retrieved_evidence,
            routing_decision=routing_decision,
            predicted_reply=predicted_reply,
        )

        raw_response = None
        parse_error = None
        schema_error = None
        call_error = None
        scores = None

        client = self._get_llm_client()
        for attempt in range(5):
            try:
                raw_response = client.generate_reply(prompt=prompt_text, temperature=TEMPERATURE)
                call_error = None
                time.sleep(0.5)  # Brief pacing sleep
                break
            except Exception as exc:
                exc_str = str(exc)
                call_error = f"LLM API call failed: {exc}"
                is_rate_limit = (
                    "rate_limit" in exc_str.lower()
                    or "429" in exc_str
                    or "resource_exhausted" in exc_str.lower()
                    or "quota" in exc_str.lower()
                )
                if is_rate_limit:
                    # Honour retryDelay from Groq / Gemini error response
                    delay = _parse_retry_delay(exc_str, default=15.0)
                    delay = max(delay, 3.0)
                    print(f"  [RATE LIMIT: {exc_str[:120]}] attempt {attempt+1}/5 — waiting {delay:.1f}s...", flush=True)
                    time.sleep(delay)
                else:
                    time.sleep(3.0 * (attempt + 1))

        if raw_response is not None:
            parsed, parse_error = _parse_llm_response(raw_response)
            if parsed is not None:
                valid, schema_error = _validate_schema(parsed)
                if valid:
                    scores = parsed

        failure_reason = call_error or parse_error or schema_error

        if scores is not None:
            # Successful result
            result_scores = {
                "relevance": scores["relevance"],
                "grounding": scores["grounding"],
                "usefulness": scores["usefulness"],
                "tone": scores["tone"],
                "critical_error": scores["critical_error"],
                "critical_details": scores.get("critical_error_details", {}),
                "rationales": {
                    "relevance": scores.get("relevance_rationale", ""),
                    "grounding": scores.get("grounding_rationale", ""),
                    "usefulness": scores.get("usefulness_rationale", ""),
                    "tone": scores.get("tone_rationale", ""),
                    "critical_error": scores.get("critical_error_rationale", ""),
                },
                "raw_llm_response": raw_response,
            }
            cache_entry = {
                "cache_key": cache_key,
                "model_id": self.model_id,
                "prompt_version": self.PROMPT_VERSION,
                "rubric_sha256": self.rubric_sha256,
                "prompt_sha256": self.prompt_sha256,
                "generation_settings": provenance["generation_settings"],
                "llm_failure": False,
                "scores": result_scores,
                "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                # Store input hashes for audit (not full input to keep cache compact)
                "input_hash": _sha256(json.dumps({
                    "customer_message": customer_message,
                    "prior_context": prior_context,
                    "retrieved_evidence": retrieved_evidence,
                    "routing_decision": routing_decision,
                    "predicted_reply": predicted_reply,
                }, sort_keys=True)),
            }
            _append_to_cache(self.cache_path, cache_entry)
            self._cache[cache_key] = cache_entry

            return {**provenance, **result_scores, "from_cache": False}

        else:
            # FAILURE — record explicitly, do NOT substitute heuristic
            cache_entry = {
                "cache_key": cache_key,
                "model_id": self.model_id,
                "prompt_version": self.PROMPT_VERSION,
                "rubric_sha256": self.rubric_sha256,
                "prompt_sha256": self.prompt_sha256,
                "generation_settings": provenance["generation_settings"],
                "llm_failure": True,
                "failure_reason": failure_reason,
                "raw_llm_response": raw_response,
                "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            _append_to_cache(self.cache_path, cache_entry)
            self._cache[cache_key] = cache_entry

            return {
                **provenance,
                "llm_failure": True,
                "failure_reason": failure_reason,
                "from_cache": False,
                # Scores are NOT populated on failure — presence of llm_failure=True
                # signals to the caller that this row is unscored.
            }

    def batch_evaluate(
        self,
        records: List[Dict[str, Any]],
        rate_limit_delay: float = 2.5,
    ) -> Tuple[List[Dict], int, int]:
        """
        Evaluate a batch. Respects rate limits between non-cached calls.
        Returns (results, num_success, num_failed).
        """
        results = []
        num_success = 0
        num_failed = 0

        for i, rec in enumerate(records):
            result = self.evaluate_reply(
                customer_message=rec.get("customer_message", ""),
                predicted_intent=rec.get("predicted_intent", ""),
                predicted_must_escalate=bool(rec.get("predicted_must_escalate", False)),
                predicted_reply=rec.get("predicted_reply", ""),
                gold_must_escalate=bool(rec.get("gold_must_escalate", False)),
                prior_context=rec.get("prior_context", ""),
                retrieved_evidence=rec.get("retrieved_evidence", ""),
            )
            results.append(result)

            if result.get("llm_failure"):
                num_failed += 1
            else:
                num_success += 1

            # Rate limit: sleep between API calls (skip if served from cache)
            if not result.get("from_cache", False) and i < len(records) - 1:
                time.sleep(rate_limit_delay)

        return results, num_success, num_failed
