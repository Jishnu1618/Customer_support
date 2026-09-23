import sys
sys.path.insert(0, ".")
from evaluate import _load_gold, _load_system_predictions, _build_retrieved_evidence_lookup
from llm_judge import LLMRubricJudge

gold_map = _load_gold()
joined_data = _load_system_predictions()
evidence_lookup = _build_retrieved_evidence_lookup()

ex_id = "SpotifyCares:1810810:1810810:1810809"
gold = gold_map[ex_id]
pred = [p for p in joined_data["baseline_0_majority"] if p["example_id"] == ex_id][0]
evidence = evidence_lookup.get(ex_id, "(none)")

judge = LLMRubricJudge(provider="groq", model="qwen/qwen3.8-27b")

prompt = judge._build_prompt(
    customer_message=gold["message"],
    prior_context=gold.get("prior_context", ""),
    retrieved_evidence=evidence,
    routing_decision="escalate",
    predicted_reply=pred["predicted_reply"]
)
print("PROMPT LENGTH (chars):", len(prompt))
print("PROMPT ESTIMATED TOKENS:", len(prompt) // 4)

try:
    res = judge.evaluate_reply(
        customer_message=gold["message"],
        predicted_intent=pred["predicted_intent"],
        predicted_must_escalate=bool(pred["predicted_must_escalate"]),
        predicted_reply=pred["predicted_reply"],
        gold_must_escalate=bool(gold["must_escalate"]),
        prior_context=gold.get("prior_context", ""),
        retrieved_evidence=evidence,
    )
    print("RESULT:", res)
except Exception as e:
    print("EXCEPTION:", type(e), e)
