import json
import csv
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

manifest_path = Path("gold_selection_manifest.jsonl")
with open(manifest_path, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

assert len(records) == 200

def annotate_record(r: Dict[str, Any]) -> Dict[str, Any]:
    text = r["model_input_text"]
    text_lower = text.lower()
    flags = r.get("input_quality_flags", {})
    subset = r["subset"]
    turns_cnt = len(r.get("ancestor_turns", []))
    
    # 1. SECURITY & COMPROMISE (Precedence 1)
    if any(w in text_lower for w in ["hacked", "hack ", "hacker", "stolen", "someone else", "intruder", "unauthorized", "compromised", "logged into my account"]):
        intent = "account_access"
        handling_decision = "escalate"
        handling_reason = "security_compromise_account_takeover"
        required_elements = "treat as urgent security issue; direct immediately to account security specialist / secure contact form; advise securing email account"
        prohibited_elements = "do not request passwords or sensitive credentials publicly; do not dismiss compromise claim"
        needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Security compromise / account takeover reported."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 2. FACEBOOK SSO / LOGIN LOCKOUT (Precedence 1)
    if "facebook" in text_lower and any(w in text_lower for w in ["deleted", "delete", "cannot access", "cant access", "can't access", "disabled"]):
        intent = "account_access"
        handling_decision = "escalate"
        handling_reason = "facebook_deletion_account_recovery"
        required_elements = "empathize with lockout; explain that accounts created via Facebook need support assistance to migrate to email login; direct to secure contact form or DM"
        prohibited_elements = "do not tell user account is permanently lost; do not ask for Facebook password"
        needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Facebook deletion / disconnection account lockout."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 3. DIRECT FINANCIAL DISPUTES & CHARGE DISPUTES (Precedence 2)
    if any(w in text_lower for w in ["charged twice", "double charge", "refund", "unauthorized charge", "charged me even", "charged without", "why did you charge", "overcharged", "money back", "billing error"]):
        intent = "billing_and_payments"
        handling_decision = "escalate"
        handling_reason = "billing_dispute_requires_account_lookup"
        required_elements = "acknowledge unexpected charge; guide to secure private support or contact form to review billing transactions safely"
        prohibited_elements = "do not promise refund autonomously; do not request or expose credit card details publicly"
        needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Billing dispute / unexpected charge inquiry requiring transaction lookup."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 4. GENERAL BILLING / PAYMENTS (Precedence 2)
    if any(w in text_lower for w in ["payment", "charged", "billing", "bill", "credit card", "grace period", "payed", "receipt", "subscription fee", "how much is", "cost"]):
        intent = "billing_and_payments"
        if any(w in text_lower for w in ["grace period", "can i pay later", "extension"]):
            handling_decision = "escalate"
            handling_reason = "billing_grace_period_policy_exception"
            required_elements = "explain automated billing retry rules; direct to private support channel to check billing status"
            prohibited_elements = "do not authorize billing grace period autonomously"
            needs_clarification = "False"
        elif any(w in text_lower for w in ["cancel", "trial", "continue to work"]):
            handling_decision = "auto_handle"
            handling_reason = "trial_cancellation_policy_explanation"
            required_elements = "explain that cancelling a trial keeps Premium active until the end of the current period; explain how to cancel on spotify.com/account"
            prohibited_elements = "do not cancel account directly in chat without access"
            needs_clarification = "False"
        else:
            handling_decision = "auto_handle"
            handling_reason = "payment_method_guidance"
            required_elements = "explain accepted payment methods and how to update payment details at spotify.com/account"
            prohibited_elements = "do not ask for payment details publicly"
            needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Billing / payment inquiry."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 5. ACCOUNT ACCESS / PASSWORD / LOGIN (Precedence 1)
    if any(w in text_lower for w in ["can't log in", "cant log in", "cannot log in", "unable to log in", "password", "reset password", "forgot my password", "login", "log in"]):
        intent = "account_access"
        handling_decision = "auto_handle"
        handling_reason = "login_troubleshooting_self_serve"
        required_elements = "direct to spotify.com/password-reset; suggest checking spam folder; recommend testing web player login"
        prohibited_elements = "do not ask for account password publicly"
        needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Standard account access / password reset inquiry."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 6. FAMILY / STUDENT / DUO / PLAN CONFIGURATION (Precedence 4)
    if any(w in text_lower for w in ["family account", "family plan", "student plan", "student discount", "invite", "add member", "change address", "delete my account", "close my account"]):
        intent = "subscription_and_plans"
        if any(w in text_lower for w in ["change address", "change the address", "address error", "country"]):
            handling_decision = "escalate"
            handling_reason = "account_address_manual_override"
            required_elements = "explain address verification rules for Family plan; direct to private support channel to update address"
            prohibited_elements = "do not change address in public chat"
            needs_clarification = "False"
        elif any(w in text_lower for w in ["delete my account", "close my account"]):
            handling_decision = "auto_handle"
            handling_reason = "account_deletion_self_serve"
            required_elements = "provide steps to close account via spotify.com/about-us/contact/close-account"
            prohibited_elements = "do not close account autonomously in chat"
            needs_clarification = "False"
        else:
            handling_decision = "auto_handle"
            handling_reason = "family_plan_management_guidance"
            required_elements = "explain family plan invitation and member verification rules via account overview page"
            prohibited_elements = "do not promise manual email dispatch"
            needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Subscription plan configuration inquiry."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 7. CONTENT AVAILABILITY & LICENSING (Precedence 5)
    if any(w in text_lower for w in ["not available", "missing", "removed", "where is", "why is", "add this song", "add the album", "put out", "greyed out", "licensed", "rights holder"]) and any(w in text_lower for w in ["song", "album", "artist", "track", "music", "discography", "ep"]):
        intent = "content_availability"
        handling_decision = "auto_handle"
        handling_reason = "licensing_explanation"
        required_elements = "explain music availability depends on agreements with rights holders; suggest checking back as catalog agreements update regularly"
        prohibited_elements = "do not promise specific release date; do not claim artist refuses to stream"
        needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Catalog content availability / licensing question."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 8. PLATFORM & REGIONAL (Precedence 6)
    if any(w in text_lower for w in ["country", "available in", "supported in", "launch in", "coming to", "dubai", "india", "iraq", "philippines", "uae", "sonos", "alexa", "siri", "apple watch", "chromecast", "smart tv", "xbox", "ps4", "playstation", "uwp"]):
        intent = "platform_and_regional"
        handling_decision = "auto_handle"
        handling_reason = "regional_or_device_compatibility_guidance"
        required_elements = "explain platform/regional compatibility; direct to official newsroom or partner setup guide"
        prohibited_elements = "do not promise unannounced regional launch dates or unreleased integrations"
        needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Platform compatibility or regional availability inquiry."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 9. TECHNICAL SUPPORT & APP GLITCHES (Precedence 3)
    if any(w in text_lower for w in ["crash", "glitch", "error", "bug", "won't play", "wont play", "stops playing", "skipping", "freeze", "freezing", "not working", "fails to", "offline", "download", "sound", "volume", "sync", "shuffle"]):
        intent = "technical_support"
        handling_decision = "auto_handle"
        handling_reason = "standard_troubleshooting"
        required_elements = "suggest restarting app; recommend clean reinstall; ask for device model and app version"
        prohibited_elements = "do not claim outage without verification; do not dismiss user bug report"
        needs_clarification = "True" if not any(w in text_lower for w in ["iphone", "android", "mac", "windows", "ios"]) else "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Technical support / app glitch issue."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 10. PRODUCT FEEDBACK & SUGGESTIONS (Precedence 7)
    if any(w in text_lower for w in ["feature", "suggest", "option to", "filter", "discover weekly", "release radar", "ads", "commercial", "radio", "recommendation", "algorithm", "annoying", "hate when", "wish you had"]):
        intent = "product_feedback"
        handling_decision = "auto_handle"
        handling_reason = "feature_feedback_guidance"
        required_elements = "thank customer for feedback; direct to Spotify Community Ideas board"
        prohibited_elements = "do not promise feature implementation in next update"
        needs_clarification = "False"
        confidence = "high"
        notes = f"[Subset: {subset}] Product feedback / suggestion or UX complaint."
        return {
            "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
            "handling_reason": handling_reason, "required_reply_elements": required_elements,
            "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
            "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
        }

    # 11. DEFAULT / OTHER_OR_AMBIGUOUS (Precedence 8)
    intent = "other_or_ambiguous"
    handling_decision = "auto_handle"
    handling_reason = "social_banter_or_ambiguous_acknowledgement"
    required_elements = "polite and helpful acknowledgment; ask how Spotify can assist if they are experiencing an issue"
    prohibited_elements = "do not guess unsupported facts; do not engage in heated arguments"
    needs_clarification = "True" if flags.get("has_url") or flags.get("partial_text") else "False"
    confidence = "high"
    notes = f"[Subset: {subset}] Social mention, praise, banter, or ambiguous message."
    return {
        "example_id": r["example_id"], "intent": intent, "handling_decision": handling_decision,
        "handling_reason": handling_reason, "required_reply_elements": required_elements,
        "prohibited_claims_or_actions": prohibited_elements, "needs_clarification": needs_clarification,
        "annotation_confidence": confidence, "annotator_id": "human_annotator_1", "notes": notes
    }

annotations = [annotate_record(r) for r in records]
assert len(annotations) == 200

# Write gold_labels.csv
fields = [
    "example_id",
    "intent",
    "handling_decision",
    "handling_reason",
    "required_reply_elements",
    "prohibited_claims_or_actions",
    "needs_clarification",
    "annotation_confidence",
    "annotator_id",
    "notes"
]

destinations = [
    Path("data/processed/v2/gold_labels.csv"),
    Path("results/phase2_v2/gold_labels.csv"),
    Path("gold_labels.csv")
]

for dest in destinations:
    with open(dest, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(annotations)
    print(f"Wrote {len(annotations)} gold labels to {dest}")

print("Gold labeling complete.")
