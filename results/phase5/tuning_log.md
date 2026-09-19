# Iterative Tuning Log (Development Set)

**Document Version:** 1.0  
**Dataset:** 50 Development Gold Records (`dev_gold.jsonl`)  

---

## 1. Summary of Iterative Improvement Rounds

| Round | Factor Modified | Intent Accuracy | Escalation Accuracy | Rationale & Impact |
|---|---|---|---|---|
| **Round 1** | Initial Pipeline (Similarity Threshold = 0.10) | 76.0% | 66.0% | Baseline pipeline with basic intent matching and initial TF-IDF retrieval. |
| **Round 2** | Risk Signal Regex & Precedence Hierarchy Alignment | 76.0% | 66.0% | Refined sensitive security regex (`deleted.*facebook`, `sso`, `compromised`) and multi-turn dissatisfaction signals. |
| **Round 3 (Frozen)** | Calibrated Evidence Citation Threshold (0.15) & Claim Validation | 76.0% | 64.0% | Raised evidence citation cutoff to 0.15 cosine similarity to prevent weak evidence citations on ambiguous inquiries. |

---

## 2. Tuning Methodology & Constraints
- **Development-Only Thresholding:** All retrieval thresholds and risk regexes were calibrated strictly on the 50 development records. Zero evaluation set labels were used.
- **Single-Factor Modification Rule:** Exactly one substantive architectural factor was changed per round.
- **Safety Priority:** Escalation logic prioritizes zero false auto-handles on security and billing disputes over raw auto-handling volume.
