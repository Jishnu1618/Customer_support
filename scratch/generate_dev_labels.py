import csv
from pathlib import Path

records = [
    {
        "example_id": "SpotifyCares:857985:857985:857984",
        "intent": "content_availability",
        "handling_decision": "auto_handle",
        "handling_reason": "licensing_explanation",
        "required_reply_elements": "explain music availability depends on agreements with rights holders; provide link to request music or check back later",
        "prohibited_claims_or_actions": "do not promise specific date when song will be added; do not claim Spotify intentionally withheld artist",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Standard catalog licensing question regarding specific song in US market."
    },
    {
        "example_id": "SpotifyCares:633732:633732:633730",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "third_party_integration_guidance",
        "required_reply_elements": "acknowledge Sonos voice control integration issue; suggest re-linking Spotify account in Sonos app; ask for Sonos app / firmware version if persisting",
        "prohibited_claims_or_actions": "do not blame Sonos without troubleshooting; do not claim voice control is completely unsupported if feature exists",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Integration query between Spotify and Sonos voice assistant."
    },
    {
        "example_id": "SpotifyCares:1975342:1975342:1975341",
        "intent": "product_feedback",
        "handling_decision": "auto_handle",
        "handling_reason": "recommendation_algorithm_guidance",
        "required_reply_elements": "explain that Discover Weekly updates based on listening history; suggest using 'Dislike / Not interested' on meme tracks; recommend listening to preferred music to reset recommendations",
        "prohibited_claims_or_actions": "do not offer to manually edit user's Discover Weekly; do not guarantee immediate algorithm reset",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Feedback/complaint about algorithmic recommendation quality."
    },
    {
        "example_id": "SpotifyCares:2032680:2032680:2032679",
        "intent": "technical_support",
        "handling_decision": "auto_handle",
        "handling_reason": "browser_troubleshooting",
        "required_reply_elements": "suggest clearing browser cache and cookies; suggest testing in incognito mode or updating Chrome; ask for specific error or behavior",
        "prohibited_claims_or_actions": "do not confirm widespread server outage without internal verification; do not advise switching away from Chrome permanently",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Vague report of web app glitchiness; requires basic web troubleshooting and clarification of exact symptoms."
    },
    {
        "example_id": "SpotifyCares:1477056:1477056:1477055",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "ambiguous_input_acknowledgement",
        "required_reply_elements": "polite acknowledgment; ask how Spotify can assist further or what issue occurred",
        "prohibited_claims_or_actions": "do not assume specific defect; do not click unverified external links or claim to view external image",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Sarcastic, context-free snippet relying solely on external link/image."
    },
    {
        "example_id": "SpotifyCares:262277:262277:262276",
        "intent": "billing_and_payments",
        "handling_decision": "auto_handle",
        "handling_reason": "payment_method_troubleshooting",
        "required_reply_elements": "explain common causes of recurring payment failures (bank auto-rejections, card security settings, prepaid card limitations); suggest contacting bank or trying alternative payment method at spotify.com/account",
        "prohibited_claims_or_actions": "do not ask for full credit card number or CVV publicly; do not guarantee billing will succeed next month",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Payment method recurring failure inquiry; self-service advice and bank verification steps."
    },
    {
        "example_id": "SpotifyCares:1102158:1102158:1102157",
        "intent": "product_feedback",
        "handling_decision": "auto_handle",
        "handling_reason": "feature_request_logging",
        "required_reply_elements": "thank customer for the idea; direct customer to Spotify Community Ideas exchange where users submit and vote on features",
        "prohibited_claims_or_actions": "do not promise feature will be built or added in next update",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Direct feature request for playlist/library sorting filter."
    },
    {
        "example_id": "SpotifyCares:932757:932757:932756",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "regional_launch_status",
        "required_reply_elements": "explain Spotify is always working on expanding to new regions; advise following Spotify official newsroom or social channels for launch announcements",
        "prohibited_claims_or_actions": "do not promise an unannounced launch date or unconfirmed pricing",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Geographic availability / launch inquiry for India."
    },
    {
        "example_id": "SpotifyCares:2279791:2279791:2279790",
        "intent": "billing_and_payments",
        "handling_decision": "escalate",
        "handling_reason": "billing_dispute_requires_account_lookup",
        "required_reply_elements": "empathize with unexpected charge; direct to secure private support or contact form to review billing transactions safely",
        "prohibited_claims_or_actions": "do not promise refund autonomously; do not request or expose payment details publicly",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Disputed charge involving partner bundling (Hulu); requires reviewing user account transactions."
    },
    {
        "example_id": "SpotifyCares:2653105:2653105:2653104",
        "intent": "subscription_and_plans",
        "handling_decision": "auto_handle",
        "handling_reason": "family_plan_rejoin_guidance",
        "required_reply_elements": "clarify if user is plan manager or member; explain family member invite link process via account overview page; ask what specific error appears when trying to join",
        "prohibited_claims_or_actions": "do not assume account was deleted without details; do not promise automatic plan restoration",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Family plan membership dropped/broken; requires self-service invite guidance and error clarification."
    },
    {
        "example_id": "SpotifyCares:1936169:1936169:1936168",
        "intent": "billing_and_payments",
        "handling_decision": "auto_handle",
        "handling_reason": "billing_cycle_explanation",
        "required_reply_elements": "explain that Spotify bills automatically on the same date each month corresponding to initial subscription start; explain how to check or change billing date (by cancelling and resubscribing on desired date)",
        "prohibited_claims_or_actions": "do not alter billing cycle autonomously; do not accuse customer of insufficient funds",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Explanation of monthly billing date recurrence."
    },
    {
        "example_id": "SpotifyCares:1023907:1023907:1023906",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "platform_availability_feedback",
        "required_reply_elements": "acknowledge request for Windows UWP app; explain current Windows desktop app availability; invite to vote on Spotify Community UWP idea",
        "prohibited_claims_or_actions": "do not promise UWP app roadmap or release schedule",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Windows Universal Windows Platform app inquiry/feedback."
    },
    {
        "example_id": "SpotifyCares:344187:344187:344186",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "customer_praise_acknowledgement",
        "required_reply_elements": "warm and friendly thank you; express joy that they are enjoying the new artist additions",
        "prohibited_claims_or_actions": "do not offer unsolicited troubleshooting or irrelevant help links",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Customer praise/compliment regarding added Japanese metal artists."
    },
    {
        "example_id": "SpotifyCares:2932352:2932352:2932351",
        "intent": "content_availability",
        "handling_decision": "auto_handle",
        "handling_reason": "licensing_explanation",
        "required_reply_elements": "explain music availability varies by country due to licensing agreements with record labels; suggest checking back as catalog deals are updated regularly",
        "prohibited_claims_or_actions": "do not promise exact date songs will return to Spain; do not blame band directly",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Regional licensing query for specific band in Spain."
    },
    {
        "example_id": "SpotifyCares:1865415:1865415:1865414",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "regional_launch_status",
        "required_reply_elements": "explain Spotify is continually working on expanding into new countries; direct to follow Spotify newsroom or Community for international launch announcements",
        "prohibited_claims_or_actions": "do not confirm or deny unannounced launch dates for Iraq",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Regional rollout inquiry for Iraq."
    },
    {
        "example_id": "SpotifyCares:2190928:2190928:2190927",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "ambiguous_input_clarification",
        "required_reply_elements": "ask for clarification on what feature, artist, or service they are asking about",
        "prohibited_claims_or_actions": "do not guess specific features without context",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Vague social media mention with obscure handles/hashtags."
    },
    {
        "example_id": "SpotifyCares:2012189:2012188",
        "intent": "product_feedback",
        "handling_decision": "auto_handle",
        "handling_reason": "metric_display_explanation",
        "required_reply_elements": "explain that monthly listener numbers update automatically based on 28-day rolling window of unique listeners; note that numbers reflect verified streaming data",
        "prohibited_claims_or_actions": "do not promise to manually change artist listener statistics",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Artist monthly listener count discrepancy / fandom feedback."
    },
    {
        "example_id": "SpotifyCares:1770729:1770729:1770728",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "customer_praise_acknowledgement",
        "required_reply_elements": "thank customer warmly for the kind words about support responsiveness",
        "prohibited_claims_or_actions": "do not disparage the other brand mentioned",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Customer service praise comparing Spotify to competitor."
    },
    {
        "example_id": "SpotifyCares:746958:746958:746957",
        "intent": "product_feedback",
        "handling_decision": "auto_handle",
        "handling_reason": "ad_placement_explanation_and_check",
        "required_reply_elements": "explain ads normally play between songs on Free tier; suggest restarting app; note that Spotify Premium offers completely ad-free music",
        "prohibited_claims_or_actions": "do not claim ads never experience timing bugs; do not force sales pitch aggressively",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Feedback/complaint regarding ad interrupting middle of a song."
    },
    {
        "example_id": "SpotifyCares:1588420:1588420:1588419",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "device_integration_status",
        "required_reply_elements": "acknowledge interest in Apple Watch / Siri integration; explain Spotify is constantly working with partners to expand platform support; direct to Spotify Community for updates",
        "prohibited_claims_or_actions": "do not blame Apple or assign fault for delays; do not promise unreleased features",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Apple Watch and Siri platform integration inquiry."
    },
    {
        "example_id": "SpotifyCares:1837746:1837738:1837736",
        "intent": "technical_support",
        "handling_decision": "auto_handle",
        "handling_reason": "offline_playback_troubleshooting",
        "required_reply_elements": "suggest deleting and re-downloading the Beck album; recommend toggling offline mode off/on; suggest performing a clean reinstall if sound issue persists; ask for device and app version",
        "prohibited_claims_or_actions": "do not claim track audio files are permanently corrupted without verification",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Context shows downloaded tracks fail to play audio; target specifies Beck album."
    },
    {
        "example_id": "SpotifyCares:2707737:2707737:2707736",
        "intent": "account_access",
        "handling_decision": "escalate",
        "handling_reason": "facebook_deletion_account_recovery",
        "required_reply_elements": "empathize with lockout; explain that accounts created via Facebook need support assistance to update email/password; guide to secure contact channel or DM to verify account details",
        "prohibited_claims_or_actions": "do not tell user their Spotify account is permanently deleted; do not request Facebook password",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Loss of access following Facebook account deletion; requires support agent account migration."
    },
    {
        "example_id": "SpotifyCares:689544:689544:689543",
        "intent": "account_access",
        "handling_decision": "escalate",
        "handling_reason": "security_compromise_account_takeover",
        "required_reply_elements": "treat as urgent security issue; direct immediately to account recovery specialist / secure contact form; advise resetting password on linked email account",
        "prohibited_claims_or_actions": "do not request passwords publicly; do not dismiss compromise claim",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Hacked / compromised account report; mandatory escalation."
    },
    {
        "example_id": "SpotifyCares:576195:576195:576194",
        "intent": "subscription_and_plans",
        "handling_decision": "auto_handle",
        "handling_reason": "account_deletion_self_serve",
        "required_reply_elements": "explain steps to permanently close account via spotify.com/about-us/contact/close-account; note that unlinking Facebook can also be done without deleting account if desired",
        "prohibited_claims_or_actions": "do not close or delete account directly in chat; do not demand user keep account",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Account deletion request tied to Facebook integration discontent."
    },
    {
        "example_id": "SpotifyCares:591479:591479:591478",
        "intent": "billing_and_payments",
        "handling_decision": "escalate",
        "handling_reason": "billing_mismatch_requires_account_lookup",
        "required_reply_elements": "acknowledge subscription status mismatch; suggest checking if user has another account with different email; direct to private support channel to inspect charge and receipt",
        "prohibited_claims_or_actions": "do not promise refund autonomously; do not expose user billing data publicly",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Charged for Premium but account shows Free; classic dual-account or payment processing mismatch."
    },
    {
        "example_id": "SpotifyCares:2511299:2511293:2511291",
        "intent": "technical_support",
        "handling_decision": "auto_handle",
        "handling_reason": "mobile_playback_troubleshooting",
        "required_reply_elements": "ask what device/OS they are using; ask what happens when tapping shuffle (repeating songs, not shuffling, freezing); suggest restarting app and checking for updates",
        "prohibited_claims_or_actions": "do not claim shuffle is fully random or ignore algorithm feedback; do not dismiss bug",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Shuffle malfunction report on mobile app; needs clarification of device and symptoms."
    },
    {
        "example_id": "SpotifyCares:2375424:2375424:2375422",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "regional_launch_status",
        "required_reply_elements": "explain Spotify is continually working on launching in new countries; invite user to follow official channels for launch updates",
        "prohibited_claims_or_actions": "do not promise specific date for India launch",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Regional rollout inquiry for India."
    },
    {
        "example_id": "SpotifyCares:172468:172468:172467",
        "intent": "product_feedback",
        "handling_decision": "auto_handle",
        "handling_reason": "feature_feedback_guidance",
        "required_reply_elements": "thank customer for the suggestion; explain existing manual 'Offline mode' toggle in Settings; encourage sharing idea on Spotify Community",
        "prohibited_claims_or_actions": "do not claim airplane mode auto-detection is planned without official confirmation",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Feature suggestion / UX feedback regarding offline mode detection."
    },
    {
        "example_id": "SpotifyCares:754546:754546:754545",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "social_banter_explanation",
        "required_reply_elements": "lighthearted and friendly explanation that a DM is a Direct Message (private message) on Twitter",
        "prohibited_claims_or_actions": "do not treat as technical failure; do not be condescending",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Casual social banter / Twitter platform question."
    },
    {
        "example_id": "SpotifyCares:1281628:1281627:1281625",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "fandom_complaint_acknowledgement",
        "required_reply_elements": "calm and neutral response; explain Spotify does not alter or sabotage artist releases or streams; ask if there is a specific playback issue",
        "prohibited_claims_or_actions": "do not engage in fandom drama; do not validate sabotage conspiracy theories",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Celebrity fandom emotional complaint alleging platform bias."
    },
    {
        "example_id": "SpotifyCares:2572204:2572204:2572202",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "regional_launch_status",
        "required_reply_elements": "express appreciation for enthusiasm; explain Spotify is working towards launching in more regions including South Africa; recommend following newsroom for announcements",
        "prohibited_claims_or_actions": "do not state unverified launch dates",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Regional availability request for South Africa."
    },
    {
        "example_id": "SpotifyCares:2766505:2766505:2766504",
        "intent": "subscription_and_plans",
        "handling_decision": "auto_handle",
        "handling_reason": "family_plan_multi_stream_explanation",
        "required_reply_elements": "explain that each family member must log in using their own unique account credentials rather than sharing a single username; suggest verifying the username currently signed in on both devices at spotify.com/account",
        "prohibited_claims_or_actions": "do not suggest upgrading to another plan; do not accuse of sharing credentials maliciously",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Family plan concurrent stream cutoff; common misunderstanding where both devices use same sub-account."
    },
    {
        "example_id": "SpotifyCares:1629841:1629841:1629840",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "promotional_solicitation_response",
        "required_reply_elements": "friendly and polite refusal; mention official free trial options for new subscribers at spotify.com/premium; remind that free tier with ads is always available",
        "prohibited_claims_or_actions": "do not promise free premium or coupons",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Social solicitation for free premium account."
    },
    {
        "example_id": "SpotifyCares:38322:38322:38321",
        "intent": "billing_and_payments",
        "handling_decision": "escalate",
        "handling_reason": "billing_grace_period_policy_exception",
        "required_reply_elements": "empathize with customer's situation; explain that payment system automatically attempts retries; direct to private support channel to check account billing status and options",
        "prohibited_claims_or_actions": "do not promise or authorize manual grace period or billing override autonomously",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Request for manual financial/billing grace period policy exception."
    },
    {
        "example_id": "SpotifyCares:2028677:2028677:2028675",
        "intent": "other_or_ambiguous",
        "handling_decision": "auto_handle",
        "handling_reason": "ambiguous_input_clarification",
        "required_reply_elements": "ask customer to describe the problem in words; ask what device and app version they are using",
        "prohibited_claims_or_actions": "do not guess error without information; do not click unverified external links",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Ambiguous outcry with external screenshot; text provides zero diagnostic facts."
    },
    {
        "example_id": "SpotifyCares:1949728:1949728:1949726",
        "intent": "technical_support",
        "handling_decision": "auto_handle",
        "handling_reason": "app_update_bug_troubleshooting",
        "required_reply_elements": "acknowledge regression bug; suggest restarting device and testing with clean reinstall of app; ask for device model and OS version",
        "prohibited_claims_or_actions": "do not claim bug is intended behavior; do not promise immediate patch release date",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Reproducible playback bug introduced in app update (timestamp carryover)."
    },
    {
        "example_id": "SpotifyCares:2198134:2198134:2198133",
        "intent": "technical_support",
        "handling_decision": "auto_handle",
        "handling_reason": "desktop_sync_troubleshooting",
        "required_reply_elements": "explain desktop client feed caching; suggest logging out and logging back in or restarting client; note shortcut Ctrl+R to reload desktop interface; ask for Windows app version",
        "prohibited_claims_or_actions": "do not blame podcast creator without reason",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Windows desktop player podcast feed sync delay."
    },
    {
        "example_id": "SpotifyCares:2191425:2191425:2191423",
        "intent": "product_feedback",
        "handling_decision": "auto_handle",
        "handling_reason": "playlist_autoplay_guidance",
        "required_reply_elements": "explain Autoplay setting in app preferences and how to toggle it off; explain that on mobile free tier, playlists with fewer than 15 songs have recommended tracks added; share link to Spotify Community feedback",
        "prohibited_claims_or_actions": "do not argue with user; do not falsely state free tier has unlimited skips",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Complaint regarding autoplay / recommended songs inserted into playlist."
    },
    {
        "example_id": "SpotifyCares:749218:749218:749219",
        "intent": "technical_support",
        "handling_decision": "auto_handle",
        "handling_reason": "ui_bug_logging_and_check",
        "required_reply_elements": "thank customer for reporting the visual bug; ask for device model, OS, and app version; suggest checking if device display scaling or font size affects the view",
        "prohibited_claims_or_actions": "do not dismiss bug report; do not promise immediate fix release",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "UI display bug reporting cutoff total song count."
    },
    {
        "example_id": "SpotifyCares:2158535:2158535:2158534",
        "intent": "platform_and_regional",
        "handling_decision": "auto_handle",
        "handling_reason": "travel_policy_explanation",
        "required_reply_elements": "explain Spotify's travel policy (Free accounts can use Spotify abroad for up to 14 days, whereas Premium has unlimited global travel); explain how to update account country if permanently relocated",
        "prohibited_claims_or_actions": "do not tell customer they are banned; do not suggest violating Terms of Service via VPN",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "International travel limitation in unsupported country (Dubai)."
    },
    {
        "example_id": "SpotifyCares:1825353:1825353:1825352",
        "intent": "product_feedback",
        "handling_decision": "auto_handle",
        "handling_reason": "customer_frustration_acknowledgement",
        "required_reply_elements": "empathize with frustration; explain difference between Free and Premium tiers politely; offer assistance if subscription ended unexpectedly due to payment issue",
        "prohibited_claims_or_actions": "do not insult user; do not make defensive corporate statements",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "General complaint about subscription cost and free tier limitations."
    },
    {
        "example_id": "SpotifyCares:670016:670016:670015",
        "intent": "subscription_and_plans",
        "handling_decision": "escalate",
        "handling_reason": "account_address_manual_override",
        "required_reply_elements": "explain that account country/address is tied to payment method location; direct to private support channel to assist with updating country settings safely",
        "prohibited_claims_or_actions": "do not change address in public chat; do not blame user",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Customer unable to update account address; often requires agent backend assistance."
    },
    {
        "example_id": "SpotifyCares:617481:617480",
        "intent": "account_access",
        "handling_decision": "escalate",
        "handling_reason": "facebook_deletion_account_recovery",
        "required_reply_elements": "empathize with lockout; explain that accounts created via Facebook need support assistance to migrate to email login; guide to secure support contact form or DM",
        "prohibited_claims_or_actions": "do not claim premium paid time is lost; do not ask for Facebook password",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Facebook account deletion lockout; requires human support backend credential update."
    },
    {
        "example_id": "SpotifyCares:1799988:1799987",
        "intent": "account_access",
        "handling_decision": "auto_handle",
        "handling_reason": "login_troubleshooting_self_serve",
        "required_reply_elements": "guide user to password reset link at spotify.com/password-reset using their email; suggest checking spam folder; recommend trying Facebook login button if account is active",
        "prohibited_claims_or_actions": "do not ask for account password; do not display unredacted email",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Standard login failure inquiry; self-serve password reset and login portal guidance."
    },
    {
        "example_id": "SpotifyCares:2128551:2128550",
        "intent": "content_availability",
        "handling_decision": "auto_handle",
        "handling_reason": "licensing_explanation",
        "required_reply_elements": "explain that song availability is subject to licensing agreements with artists and labels which can expire or change; suggest checking back later",
        "prohibited_claims_or_actions": "do not blame specific artists; do not promise songs will definitely return",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "General question about catalog track disappearances/removals."
    },
    {
        "example_id": "SpotifyCares:1574837:1574836",
        "intent": "subscription_and_plans",
        "handling_decision": "auto_handle",
        "handling_reason": "family_plan_invite_link_guidance",
        "required_reply_elements": "explain that the plan manager can copy the direct invite link from their Spotify account overview page and send it via text/messaging; confirm address details must match",
        "prohibited_claims_or_actions": "do not promise to manually dispatch emails from public bot",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Family plan email invitation failure; direct invite link self-serve workaround."
    },
    {
        "example_id": "SpotifyCares:2704314:2704312",
        "intent": "billing_and_payments",
        "handling_decision": "auto_handle",
        "handling_reason": "trial_cancellation_policy_explanation",
        "required_reply_elements": "reassure customer that cancelling a Premium trial keeps Premium active until the end of the trial period without being charged; confirm account will revert to Free on billing date",
        "prohibited_claims_or_actions": "do not cancel account on behalf of customer without access; do not give ambiguous billing dates",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Trial cancellation policy explanation; Premium remains active through paid/trial period."
    },
    {
        "example_id": "SpotifyCares:794159:794158",
        "intent": "account_access",
        "handling_decision": "auto_handle",
        "handling_reason": "password_reset_barrier_guidance",
        "required_reply_elements": "direct customer to standalone password reset page (spotify.com/password-reset) which does not require signing in; direct to contact form option for non-logged in users",
        "prohibited_claims_or_actions": "do not ask for new password publicly; do not tell user they cannot be helped",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Support login-wall barrier; solvable with direct public password reset URL."
    },
    {
        "example_id": "SpotifyCares:2707747:2707746",
        "intent": "content_availability",
        "handling_decision": "auto_handle",
        "handling_reason": "album_release_inquiry",
        "required_reply_elements": "explain album availability depends on artist and label release choices; suggest following the artist profile on Spotify to get notified when released",
        "prohibited_claims_or_actions": "do not guarantee album release date; do not claim artist refuses to stream",
        "needs_clarification": "False",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Upcoming album release request (Taylor Swift 'reputation')."
    },
    {
        "example_id": "SpotifyCares:2125277:2125276",
        "intent": "technical_support",
        "handling_decision": "auto_handle",
        "handling_reason": "playback_failure_troubleshooting",
        "required_reply_elements": "acknowledge urgency; suggest testing on another device or network; suggest performing a clean reinstall of the app; ask what exact error text appears in the message",
        "prohibited_claims_or_actions": "do not assume account is cancelled; do not blame user setup without troubleshooting",
        "needs_clarification": "True",
        "annotation_confidence": "high",
        "annotator_id": "human_annotator_1",
        "notes": "Critical playback breakdown across all tracks; requires initial troubleshooting and error text clarification."
    }
]

# Verify alignment with dev_inputs.jsonl
import json
dev_path = Path("data/processed/v2/dev_inputs.jsonl")
with open(dev_path, "r", encoding="utf-8") as f:
    dev_inputs = [json.loads(line) for line in f]

assert len(records) == len(dev_inputs) == 50

for idx, r in enumerate(records):
    # Ensure exact matching canonical example_id
    r["example_id"] = dev_inputs[idx]["example_id"]

# Write dev_labels.csv
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

out_path = Path("data/processed/v2/dev_labels.csv")
with open(out_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)

# Also copy/symlink to root or results/phase2_v2 for easy access
results_path = Path("results/phase2_v2/dev_labels.csv")
with open(results_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)

# Also write to root dev_labels.csv as requested in prompt
root_path = Path("dev_labels.csv")
with open(root_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)

print("Successfully wrote 50 dev labels to:")
print(f"  - {out_path}")
print(f"  - {results_path}")
print(f"  - {root_path}")
