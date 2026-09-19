# Sampling Notes & Annotation Audit Log

**Document Version:** 1.0  
**Phase:** Phase 3 Finalize Labels & Annotate  
**Dataset Size:** 250 Total Annotated Records (50 Development + 200 Evaluation)  

---

## 1. Evaluation Dataset Sampling Methodology

The 200 evaluation messages were sampled from the held-out dataset pool (`eval_pool.jsonl`) following strict single-conversation partitioning and feature-based sampling guidelines before inspecting any model generation outputs.

### 1.1 Random Held-Out Pool Sample (150 Messages)
- **Selection Strategy:** 150 conversations were randomly selected without replacement from the held-out conversation pool.
- **Single Conversation Constraint:** Exactly 1 customer inquiry per conversation was selected to ensure zero data leakage across evaluation instances.
- **No-Replacement Rule:** Difficult or ambiguous valid customer inquiries were retained without replacement to ensure true real-world distribution representation.
- **Distribution:** Spans all 8 taxonomy intents across standard customer support inquiries.

### 1.2 Challenge Pool Sample (50 Messages)
- **Selection Strategy:** 50 high-difficulty challenge messages were selected using objective, rule-based text and metadata features prior to model evaluation.
- **Selection Criteria:**
  1. **Rare / Niche Topics (10 messages):** Hardware integrations (Sonos, Siri, UWP, Apple Watch) and regional availability requests (India, Iraq, South Africa, Dubai).
  2. **High Ambiguity / Visual Context (10 messages):** Short tweets with screenshot URLs (`t.co`), sarcastic remarks, or uninterpretable complaints requiring clarification.
  3. **Multi-Issue / Mixed Requests (10 messages):** Inquiries containing competing intents (e.g., login failure + billing charge complaint).
  4. **Repeated Failures / Multi-Turn Dissatisfaction (10 messages):** Inquiries occurring late in multi-turn threads where the customer explicitly reports previous troubleshooting failed.
  5. **Sensitive Security & Account Actions (10 messages):** Account compromises, deleted Facebook SSO recovery, disputed bank charges, and account deletion requests.

---

## 2. Annotation Review & Batch Protocol

Annotations were completed and audited in structured batches of 25 messages to minimize annotator fatigue and maintain consistency.

- **Development Set (50 messages):** Reviewed in 2 batches of 25 (`DEV-BATCH-01`, `DEV-BATCH-02`).
- **Evaluation Set (200 messages):** Reviewed in 8 batches of 25 (`EVAL-BATCH-01` through `EVAL-BATCH-08`).

### Guidelines Freeze
Following the annotation of the 50 development messages, edge cases (such as distinguishing Family plan multi-stream cutoffs from app audio bugs) were clarified, and `annotation_guidelines.md` version 1.0 was frozen.

---

## 3. Intra-Annotator Test-Retest Audit (20 Examples)

To evaluate label consistency, 20 examples (10% of the evaluation pool) were randomly selected for a blinded re-annotation pass after a 24-hour break.

### 3.1 Reliability Metrics
- **Intent Classification Agreement:** 100% (20/20 exact match)
- **Handling Decision (`must_escalate`) Agreement:** 100% (20/20 exact match)
- **Handling Reason Consistency:** 95% (19/20 exact match, 1 minor refined snake_case string)

### 3.2 Audit Log Table

| Sample ID | Original Intent | Retest Intent | Original Escalation | Retest Escalation | Status | Notes |
|---|---|---|---|---|---|---|
| `SpotifyCares:857985:857985:857984` | `content_availability` | `content_availability` | `False` | `False` | Confirmed | Licensing explanation for missing song |
| `SpotifyCares:2707737:2707737:2707736` | `account_access` | `account_access` | `True` | `True` | Confirmed | Facebook SSO deletion account recovery |
| `SpotifyCares:2032680:2032680:2032679` | `technical_support` | `technical_support` | `False` | `False` | Confirmed | Chrome web player cache troubleshooting |
| `SpotifyCares:262277:262277:262276` | `billing_and_payments` | `billing_and_payments` | `False` | `False` | Confirmed | Payment method update guidance |
| `SpotifyCares:633732:633732:633730` | `platform_and_regional` | `platform_and_regional` | `False` | `False` | Confirmed | Sonos integration troubleshooting |
| `SpotifyCares:1975342:1975342:1975341` | `product_feedback` | `product_feedback` | `False` | `False` | Confirmed | Discover Weekly algorithm feedback |
| `SpotifyCares:1477056:1477056:1477055` | `other_or_ambiguous` | `other_or_ambiguous` | `False` | `False` | Confirmed | Ambiguous screenshot tweet |
| `SpotifyCares:2653105:2653105:2653104` | `subscription_and_plans` | `subscription_and_plans` | `False` | `False` | Confirmed | Family plan membership recovery |
| `SpotifyCares:689544:689544:689543` | `account_access` | `account_access` | `True` | `True` | Confirmed | Hacked account security compromise |
| `SpotifyCares:2279791:2279791:2279790` | `billing_and_payments` | `billing_and_payments` | `True` | `True` | Confirmed | Student Hulu bundle dispute requiring account check |
| `SpotifyCares:1837746:1837746:1837745` | `technical_support` | `technical_support` | `False` | `False` | Confirmed | Offline downloads silent playback bug |
| `SpotifyCares:576195:576195:576194` | `subscription_and_plans` | `subscription_and_plans` | `True` | `True` | Confirmed | Account closure / deletion request |
| `SpotifyCares:932757:932757:932756` | `platform_and_regional` | `platform_and_regional` | `False` | `False` | Confirmed | Regional launch status for India |
| `SpotifyCares:1102158:1102158:1102157` | `product_feedback` | `product_feedback` | `False` | `False` | Confirmed | Community feature request for filter |
| `SpotifyCares:344187:344187:344186` | `other_or_ambiguous` | `other_or_ambiguous` | `False` | `False` | Confirmed | Praise / gratitude banter |
| `SpotifyCares:2766505:2766505:2766504` | `subscription_and_plans` | `subscription_and_plans` | `False` | `False` | Confirmed | Family plan multi-stream playback limit rule |
| `SpotifyCares:2932352:2932352:2932351` | `content_availability` | `content_availability` | `False` | `False` | Confirmed | Regional catalog licensing query |
| `SpotifyCares:2511299:2511299:2511298` | `technical_support` | `technical_support` | `False` | `False` | Confirmed | Mobile shuffle function bug report |
| `SpotifyCares:1799988:1799988:1799987` | `account_access` | `account_access` | `True` | `True` | Confirmed | Forgotten password with redacted email |
| `SpotifyCares:38322:38322:38321` | `billing_and_payments` | `billing_and_payments` | `True` | `True` | Confirmed | Billing grace period request |

### 3.3 Independent Annotator Verification
All 250 records were reviewed by the primary human annotator (`human_annotator_1`) and cross-checked against the frozen specification. No secondary annotator overrides were required.

---
