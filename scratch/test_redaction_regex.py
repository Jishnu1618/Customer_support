import re

CANDIDATES = ["SpotifyCares", "AppleSupport", "AskPlayStation"]

def redact_sensitive_info(text: str, candidate_brands=CANDIDATES) -> str:
    if not text:
        return text

    brand_handles = {b.lower() for b in candidate_brands} | {
        "spotifycares", "spotify", "spotifyusa", "spotifyuk", "spotifyhelp",
        "spotifystatus", "spotifyjobs", "applesupport", "askplaystation",
        "amazonhelp", "tmobilehelp", "uber_support", "microsofthelps"
    }

    # 1. Dataset privacy placeholders normalization & idempotency protection
    text = re.sub(r'id::\d+__credit_card__:', '[CREDIT_CARD_REDACTED]:', text)
    text = re.sub(r'\b__credit_card__\b', '[CREDIT_CARD_REDACTED]', text)
    text = re.sub(r'\b__email__\b', '[EMAIL_REDACTED]', text)
    text = re.sub(r'\b__phone__\b', '[PHONE_REDACTED]', text)

    # 2. Contextual bare-username handling
    def username_replacer(match: re.Match) -> str:
        prefix = match.group(1)
        val = match.group(2)
        quote = match.group(3) or ""

        # Don't replace if already a placeholder
        if val in {"[CUSTOMER_USERNAME]", "[CUSTOMER_NAME]", "[CUSTOMER_HANDLE]", "@[CUSTOMER_HANDLE]"}:
            return match.group(0)
        if val.startswith("[") and val.endswith("]"):
            return match.group(0)

        lower_val = val.lstrip("@").lower()
        if lower_val in {
            "not", "none", "unknown", "lost", "forgotten", "n/a", "null", "blank",
            "working", "broken", "fine", "ok", "okay", "good", "bad", "active",
            "locked", "disabled", "blocked", "banned", "hacked", "suspended",
            "changed", "new", "old", "same", "different", "invalid", "correct",
            "wrong", "missing", "private", "public", "already", "still"
        }:
            return match.group(0)
        if lower_val in brand_handles or lower_val in {"spotify", "apple", "google", "android", "iphone", "ios", "windows", "mac"}:
            return match.group(0)
        # Avoid error codes
        if re.match(r'^(?:0x[0-9a-fA-F]+|\d{3,4})$', val):
            return match.group(0)

        return f"{prefix}[CUSTOMER_USERNAME]{quote}"

    username_pattern = re.compile(
        r'(\b(?:my\s+)?(?:official\s+)?(?:spotify\s+)?(?:account\s+)?(?:user\s*name|username|screen\s*name|user\s*id|login(?:\s+name|\s+id)?|account(?:\s+name|\s+id)?|handle)\s*(?:is|:|=|-|\bis\s+called)\s*[\'"]?)(@?[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)*)([\'"]?)',
        re.IGNORECASE
    )
    text = username_pattern.sub(username_replacer, text)

    # 3. Emails (must be before handles so @domain is not matched as handle)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL_REDACTED]', text)

    # 4. Customer handles (@username) while keeping brand handles intact
    def handle_replacer(match: re.Match) -> str:
        handle_name = match.group(1)
        if handle_name.startswith("[") and handle_name.endswith("]"):
            return match.group(0)
        if handle_name.lower() in brand_handles:
            return f"@{handle_name}"
        return "@[CUSTOMER_HANDLE]"

    text = re.sub(r'@([A-Za-z0-9_]+)', handle_replacer, text)

    # 5. Phone numbers (avoid matching software versions like v8.4.22.857 and error codes)
    text = re.sub(r'(?<![vV\d.])(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)(?!\.\d)', '[PHONE_REDACTED]', text)

    # 6. Bare customer greeting names (e.g., "Hey Vanessa," -> "Hey [CUSTOMER_NAME],")
    reserved_greeting_targets = brand_handles | {
        "spotify", "spotifycares", "apple", "amazon", "google", "playstation",
        "customer_name", "customer_username", "there", "team", "everyone", "guys"
    }

    def greeting_replacer(match: re.Match) -> str:
        greeting = match.group(1)
        name = match.group(2)
        if name.lower() in reserved_greeting_targets:
            return match.group(0)
        return f"{greeting} [CUSTOMER_NAME]"

    text = re.sub(r'\b(Hey|Hi|Hello|Dear)\s+([A-Z][a-z]{2,15})\b', greeting_replacer, text)

    return text

# Test cases
tests = [
    ("My username is listener_demo96", "My username is [CUSTOMER_USERNAME]"),
    ("My username is locked", "My username is locked"),
    ("My account name is still broken", "My account name is still broken"),
    ("username: listener_demo96.", "username: [CUSTOMER_USERNAME]."),
    ("Spotify username is 'listener_demo96'", "Spotify username is '[CUSTOMER_USERNAME]'"),
    ("My user name is @listener_demo96, help!", "My user name is [CUSTOMER_USERNAME], help!"),
    ("account name is listener_demo96", "account name is [CUSTOMER_USERNAME]"),
    ("Hello support team, my official Spotify username is listener_demo96_secure_id!", "Hello support team, my official Spotify username is [CUSTOMER_USERNAME]!"),
    ("Phone: +1 555-234-5678.", "Phone: [PHONE_REDACTED]."),
    ("Hey Jordan, my email is alice@test.com and phone is 555-867-5309", "Hey [CUSTOMER_NAME], my email is [EMAIL_REDACTED] and phone is [PHONE_REDACTED]"),
    ("Hey Spotify, I have error 0xc0000005 on iPhone 12 iOS 15.1.1 Spotify v8.4.22.857 code 404", "Hey Spotify, I have error 0xc0000005 on iPhone 12 iOS 15.1.1 Spotify v8.4.22.857 code 404"),
    ("Dataset placeholder __email__ and __phone__", "Dataset placeholder [EMAIL_REDACTED] and [PHONE_REDACTED]"),
    ("Already redacted @[CUSTOMER_HANDLE] and [CUSTOMER_USERNAME] and [EMAIL_REDACTED]", "Already redacted @[CUSTOMER_HANDLE] and [CUSTOMER_USERNAME] and [EMAIL_REDACTED]"),
]

for orig, expected in tests:
    res = redact_sensitive_info(orig)
    assert res == expected, f"Failed: '{res}' != '{expected}'"
    # Idempotency check
    res2 = redact_sensitive_info(res)
    assert res2 == res, f"Idempotency failed: '{res2}' != '{res}'"

print("All scratch redaction tests passed!")
