import sys
sys.path.insert(0, ".")
import json
from evaluate import _load_gold, _load_system_predictions

gold = _load_gold()
preds = _load_system_predictions()

for sys_id, p_list in preds.items():
    print(f"=== {sys_id} ===")
    for subset in ["random", "challenge"]:
        sub_p = [p for p in p_list if gold[p["example_id"]].get("subset") == subset]
        acc = sum(1 for p in sub_p if p["predicted_intent"] == gold[p["example_id"]]["intent"]) / len(sub_p)
        esc_gold = [p for p in sub_p if gold[p["example_id"]]["must_escalate"]]
        esc_num = sum(1 for p in esc_gold if p["predicted_must_escalate"])
        esc_rec = esc_num / len(esc_gold) if esc_gold else 1.0
        cov = sum(1 for p in sub_p if not p["predicted_must_escalate"]) / len(sub_p)
        auto_p = [p for p in sub_p if not p["predicted_must_escalate"]]
        unsafe_num = sum(1 for p in auto_p if gold[p["example_id"]]["must_escalate"])
        unsafe = unsafe_num / len(auto_p) if auto_p else 0.0
        print(f"  {subset} (N={len(sub_p)}): Intent Acc={acc:.1%} ({sum(1 for p in sub_p if p['predicted_intent'] == gold[p['example_id']]['intent'])}/{len(sub_p)}), Esc Recall={esc_rec:.1%} ({esc_num}/{len(esc_gold)}), Cov={cov:.1%} ({len(auto_p)}/{len(sub_p)}), Unsafe Rate={unsafe:.1%} ({unsafe_num}/{len(auto_p)})")
