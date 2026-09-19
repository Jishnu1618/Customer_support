# Data Quality & Extraction Audit Report

This report documents the raw inspection of Spotify 005, 017, and 024 against raw CSV/SQLite rows without inventing missing text or making unverified assumptions.

---

## 1. Raw Row Inspection Findings

### Spotify 005 (Root Tweet ID: `337851`)
- **Customer Tweet (`337851`)**: `@115888 so please reach back to me as some as possible Spotify please`
- **Brand Reply (`337849`)**: `@196643 Hey! Don’t worry, we can help. What’s happening exactly? Can you let us know the device/OS you’re using? /SU`
- **Audit Analysis**:
  - The customer turn starts with lowercase `"so please reach back to me..."` without an `in_response_to_tweet_id` link to a preceding message.
  - This indicates a **suspected multipart / partial text continuation** where the preceding tweet was either uncollected in TWCS or unlinked in Twitter's reply chain.
  - **Flag Assigned**: `suspected_multipart: true`. No missing text is invented.

### Spotify 017 (Root Tweet ID: `1366580`)
- **Customer Tweet (`1366580`)**: `Hey @SpotifyCares someone is using my Spotify account on devices I don't recognize, I think I may have been hacked. Help?`
- **Brand Reply (`1366579`)**: `@438120 Hi Alex, we’re sorry to hear that. Check out https://t.co/QHn3ok8y2n for what to do next /JQ`
- **Audit Analysis**:
  - The brand reply refers the customer to an external shortened URL (`https://t.co/QHn3ok8y2n`).
  - **Flag Assigned**: `external_context_required: true`. The bare URL does not expose internal policy text, so inference engines must treat this as requiring external reference resolution or human review.

### Spotify 024 (Root Tweet ID: `462662`)
- **Customer Tweet (`462662`)**: `Premium gives you unlimited skips. Get 3 months now for just $0.99. https://t.co/QrFG4WEpy1`
- **Brand Reply (`462660`)**: `@224966 Hey there! Can you DM us your account's email address or username? We'll take a look /NS https://t.co/ldFdZRiNAt`
- **Audit Analysis**:
  - The brand turn asks for private details via Direct Message and includes a DM deep link (`https://t.co/ldFdZRiNAt`).
  - **Flag Assigned**: `external_context_required: true`. Demonstrates DM handoff requirement for private investigations.

---

## 2. Redaction Verification & Bare Username Synthetic Test

- Synthetic test added: `test_redact_bare_username_synthetic` in `tests/test_sample_brand_conversations.py`.
- Evaluates bare customer name redactions (e.g. `Hey Vanessa, ...` -> `Hey [CUSTOMER_NAME], ...`).
- **Safety Note**: Passing redaction unit tests verifies regex transformation rules; it does not guarantee structural tree reconstruction.

---

## 3. Split Isolation & Model Context Guidelines

- **Split Isolation**: Dataset partitioning (Train / Dev / Test) must operate at the **full conversation group level** (grouped by root tweet ID) to prevent data leakage.
- **Model Context**: Model inputs must be built strictly from the **ancestor path** up to the target customer turn. Future turns and descendant branches must never be fed into inference models.
