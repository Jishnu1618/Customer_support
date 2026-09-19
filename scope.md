# Reply Agent scope

Status: SpotifyCares selected for implementation from the 91 supplied review transcripts. Confirm sufficient eligible historical conversations during Phase 2. This selection and document are AI-assisted analysis, not human golden-set annotation.

## Objective
- Classify the main intent of an English customer message directed to Spotify support.
- Draft an appropriate next response supported by separate historical conversations.
- Decide auto_handle or escalate with specific reason codes and evidence IDs.
- Evaluate offline. Auto-handle means eligible to send without review, not successful issue resolution.

## Inputs and outputs
- Input: current customer turn and relevant prior conversation context only.
- Output: example_id, intent, draft_reply, decision, reason_codes, evidence_ids, status, latency, and token usage.
- Future replies and test annotations never enter inference or retrieval.

## Capabilities
- Ask non-sensitive diagnostic questions about device, OS, app version, and visible error text.
- Suggest low-risk troubleshooting only when evidence applies and the customer has not already tried it unsuccessfully.
- Explain the need for human review when investigation or authority is unavailable.
- Use historical support behaviour as evidence, not as current verified product policy.

## Exclusions and escalation
- No account access, refunds, subscription changes, actual DM sending, ticket creation, or real-world customer messaging.
- Do not request passwords, payment details, or account identifiers in public replies.
- Escalate suspected compromise, account-specific billing/investigation, unsupported current policy/status requests, and insufficient or contradictory evidence.
- Do not claim that a refund was processed, a DM was sent, an engineer was assigned, or feedback was forwarded.
- Do not reproduce old promotional prices, release availability, licensing guarantees, or unverified shortened URLs as present facts.
- Do not infer screenshot contents or linked-page instructions from a bare URL. Keep ambiguous eligible messages and escalate or request safe clarification according to the frozen policy.
- Non-English target messages are outside this evaluation scope; record exclusions. Language is determined from the customer input, not the brand reply.

## Data and experiment
- Target 3,000 eligible historical conversations; 50 human-labelled development messages; 200 human-labelled evaluation messages.
- Evaluation: 150 random and 50 challenge messages, reported separately; one target turn per conversation group.
- Three systems: majority/always-escalate baseline; keyword/template baseline; TF-IDF plus LLM agent.
- Reserve every inspected brand-review conversation for exploration/historical/development use. Exclude any overlapping conversation group from final evaluation.
- Final labels and judge validation ratings must be personally reviewed by a human. AI analysis does not meet the hand-labelling requirement on its own.

## Provisional issue groups
Use these for exploration, not frozen final labels:
1. playback_or_app_issue
2. login_or_account_security
3. billing_or_payment
4. subscription_or_plan_access
5. music_catalog_or_content
6. feature_or_product_feedback
7. account_settings_or_region
8. other_or_unclear

Define boundaries from the 50 development examples. For example, a disputed charge belongs to billing; paid Premium not activating belongs to plan access. A security flag must remain independent of intent.

## Completion criteria
- Scope and brand choice are recorded.
- Extraction/privacy audit issues are corrected before generating final splits.
- Final claims are limited to measured eligible traffic and clearly identify whether quality was human-assessed or LLM-judged.
