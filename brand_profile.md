# Brand selection review

## Decision
Select SpotifyCares for this offline prototype. The reason is a manageable service-focused issue space and useful examples of both low-risk public guidance and necessary human handoff. It is not the brand with the fewest DM mentions, and this small sample cannot establish population-wide superiority.

Review provenance: AI-assisted inspection of all 91 supplied conversation transcripts and consistency checks against sampling_manifest.json and review_scores.csv. The review sheet remains unmodified and empty; no human ratings are claimed. Brand tweet volumes below were reported by the user in the earlier dataset profile and were not independently recalculated here.

## Comparison
| Brand | Reported outbound tweets | Review records | Marked structurally complete by sampler | Conversations containing explicit brand DM language |
|---|---:|---:|---:|---:|
| SpotifyCares | 43,265 | 31 | 30 | 15/31 |
| AppleSupport | 106,860 | 30 | 30 | 17/30 |
| AskPlayStation | 19,098 | 30 | 30 | 10/30 |

DM language includes requests, stated DM actions, and conditional invitations, in any displayed brand turn. It is a transcript feature, not an escalation gold label, a DM-only rate, or a resolution rate. Spotify's incomplete record mentions DM; among its 30 marked complete records the count is 14/30. Counts include non-English and otherwise problematic records. These are exploratory samples selected until 30 structurally complete records were found, not unbiased production estimates. Unique roots do not establish uniform conversation sampling; source code is needed to verify whether sampling began from tweets or conversation groups.

## Evidence supporting Spotify
- SpotifyCares_CONV_030: connection/playback problem; support suggests logging out, restarting the device, and logging back in; the customer explicitly reports it is sorted. This is a reusable attempted-action pattern with a reported successful outcome, not a universal fix.
- SpotifyCares_CONV_001: asks for device/app/OS details and suggests restarting. Useful diagnostic sequence; no confirmed outcome is shown.
- SpotifyCares_CONV_012 and 020: requests device or version information. These demonstrate useful next questions without proving resolution.
- SpotifyCares_CONV_021: compromised account is handed to private support, followed by reported recovery. Recovery is confirmed, but the private method is unobserved and cannot be automated from this evidence.
- SpotifyCares_CONV_027: duplicate charge leads to account investigation. A clear example for required review.
- SpotifyCares_CONV_008 and 014: old content availability and promotional eligibility show why historical replies cannot be treated as current policy.

## Why the other candidates were not selected
- AppleSupport: the sample spans phones, watches, computers, connectivity, billing, and OS-specific issues. Many replies hand off to DM. CONV_001 also shows a suggested restart was already tried; CONV_020 shows an article referral the customer found unhelpful. These are valuable failure cases but increase scope and evidence burden.
- AskPlayStation: fewer explicit DM mentions in this sample, and several public instructions. However, examples cover console settings, account activation, games, and Vue television service. CONV_026–028 depend on settings changes, external instructions, or missing visual details. The sample therefore has a broader and more consequential troubleshooting burden for this small prototype.

## Limits
- These files do not establish at least 3,000 eligible conversations; confirm that during corpus extraction.
- “Thanks” is not proof of a fix. A self-reported fix does not establish that the brand caused it.
- A connected path can still contain missing semantic context, partial multi-part responses, external images, or multiple people.
- No original CSV, SQLite index, or extraction implementation was provided for this audit, so edge correctness, duplicate handling, and RNG behaviour cannot be independently certified.
- The samples contain 2017 messages. No historical product statement in this review is asserted as current advice.
