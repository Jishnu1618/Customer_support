# Development Review Notes (50 Frozen Development Inputs)

This document records the empirical findings from reviewing all 50 frozen development inputs (`data/processed/v2/dev_inputs.jsonl`) and their allowed conversation context.

---

## 1. Provenance & Isolation Confirmation
- **Development Set Size**: 50 distinct conversation groups.
- **Evaluation Pool Isolation**:
  - Direct dev group overlap with evaluation pool: **0**
  - Dev duplicate cluster overlap with evaluation pool: **0**
  - All 121 past review groups and their duplicate clusters in evaluation pool: **0**
- **Protected Integrity Verification**:
  - `results/brand_review/review_scores.csv`: Verified unmodified (`4447e61475fd...`).
  - `results/brand_review/original_sampling_manifest.json`: Verified unmodified (`b3087587be98...`).
  - `results/brand_review/sampling_manifest_original_uploaded.json`: Verified unmodified (`b3087587be98...`).
  - `results/brand_review/sampling_manifest_v1.json`: Verified unmodified (`100a607c3fcd...`).
  - `results/brand_review/sampling_manifest.json`: Verified unmodified (`d0ac2d9cc582...`).

---

## 2. Empirical Review of 50 Development Cases

| # | Example ID | Summary of Customer Inquiry | Key Flags / Context | Emerging Category |
|---|---|---|---|---|
| 1 | `857985:857985:857984` | Christina Milian song not available on US Spotify | Single turn | Content Availability |
| 2 | `633732:633732:633730` | Cannot start Spotify music/playlists with new Sonos voice control | Single turn, hardware integration | Platform & Regional |
| 3 | `1975342:1975342:1975341` | Discover Weekly playlist full of memes | Single turn, recommendation feedback | Product Feedback |
| 4 | `2032680:2032680:2032679` | Chrome web app glitchy / freezing | Single turn, browser app issue | Technical Support |
| 5 | `1477056:1477056:1477055` | "Thanks. Try harder plz😉 https://t.co/Kf9KSF50hJ" | URL only, sarcastic, unclear | Other / Ambiguous |
| 6 | `262277:262277:262276` | Has to update payment info every month | Single turn, recurring payment annoyance | Billing & Payments |
| 7 | `1102158:1102158:1102157` | Requesting a "most played" filter option | Feature request | Product Feedback |
| 8 | `932757:932757:932756` | Asking if launching services in India | Country launch inquiry | Platform & Regional |
| 9 | `2279791:2279791:2279790` | Charged for student Hulu discount without signing up | Billing dispute / unexpected charge | Billing & Payments |
| 10 | `2653105:2653105:2653104` | Family account stopped working, can't restore | Plan issue / family sharing | Subscription & Plans |
| 11 | `1936169:1936169:1936168` | Takes out money before paycheck arrives | Billing timing complaint | Billing & Payments |
| 12 | `1023907:1023907:1023906` | Demanding UWP Windows app for Premium users | Platform / OS app request | Platform & Regional |
| 13 | `344187:344187:344186` | Praise for adding Galneryus and Maximum the Hormone | Positive feedback / compliment | Other / Ambiguous |
| 14 | `2932352:2932352:2932351` | Children of Bodom songs missing in Spain | Regional licensing | Content Availability |
| 15 | `1865415:1865415:1865414` | Inquiring if Spotify will be supported in Iraq | Regional availability inquiry | Platform & Regional |
| 16 | `2190928:2190928:2190927` | Vague query about when adding another user / hashtag | Unclear banter | Other / Ambiguous |
| 17 | `2012189:2012189:2012188` | Asking to fix Camila monthly listener count | Artist metric feedback | Product Feedback |
| 18 | `1770729:1770729:1770728` | Meta praise of Spotify response vs other brand | Commentary on support | Other / Ambiguous |
| 19 | `746958:746958:746957` | Complaining about ad playing in middle of song | Ad insertion complaint | Product Feedback |
| 20 | `1588420:1588420:1588419` | Asking for Apple Watch and Siri integration support | Device compatibility inquiry | Platform & Regional |
| 21 | `1837746:1837738:1837736` | Downloaded Beck album tracks do not play audio | 2 turns (prior turn describes bug) | Technical Support |
| 22 | `2707737:2707737:2707736` | Deleted Facebook and now cannot log into Spotify | SSO disconnection lockout | Account Access |
| 23 | `689544:689544:689543` | Premium account compromised / hacked | Security / account takeover | Account Access |
| 24 | `576195:576195:576194` | Demanding to delete account disconnected from FB | Account closure / deletion | Subscription & Plans |
| 25 | `591479:591479:591478` | Charged for Premium but account shows Free tier | Subscription status mismatch | Billing & Payments |
| 26 | `2511299:2511293:2511291` | Mobile shuffle playback broken | 2 turns (reply to promo tweet) | Technical Support |
| 27 | `2375424:2375424:2375422` | When are you coming to India? | Regional rollout | Platform & Regional |
| 28 | `172468:172468:172467` | Feature request: auto-detect airplane mode for downloads | Feature suggestion | Product Feedback |
| 29 | `754546:754546:754545` | "Hey what's a DM 😂?" | Conversational banter | Other / Ambiguous |
| 30 | `1281628:1281627:1281625` | "Stop sabotaging Selena on Spotify" | Fandom complaint | Other / Ambiguous |
| 31 | `2572204:2572204:2572202` | Make app available in South Africa | Regional rollout | Platform & Regional |
| 32 | `2766505:2766505:2766504` | Family account cuts off PC when wife listens at home | Multi-stream Family rules | Subscription & Plans |
| 33 | `1629841:1629841:1629840` | Asking for free premium | Promotional solicitation | Other / Ambiguous |
| 34 | `38322:38322:38321` | Requesting payment grace period for premium | Billing / payment extension | Billing & Payments |
| 35 | `2028677:2028677:2028675` | "Please explain yourself!! why is this happening [URL]" | Image-dependent exclamation | Other / Ambiguous |
| 36 | `1949728:1949728:1949726` | App update bug: songs start at timestamp of previous song | Playback bug after update | Technical Support |
| 37 | `2198134:2198134:2198133` | Podcasts taking long to sync on Windows desktop app | Desktop app sync delay | Technical Support |
| 38 | `2191425:2191425:2191423` | Complaint: unsolicited recommended songs inserted in playlist | Playlist behavior feedback | Product Feedback |
| 39 | `749218:749218:749219` | UI bug: total song count is cutoff | Visual display bug | Technical Support |
| 40 | `2158535:2158535:2158534` | Cannot use Spotify account while in Dubai | Travel / regional licensing rule | Platform & Regional |
| 41 | `1825353:1825353:1825352` | Forced off premium, venting about corporate greed | Free tier change complaint | Product Feedback |
| 42 | `670016:670016:670015` | Cannot change billing address/country on account | Account settings / location update | Subscription & Plans |
| 43 | `617481:617481:617480` | Deleted Facebook and cannot access connected Premium account | SSO disconnection lockout | Account Access |
| 44 | `1799988:1799988:1799987` | Unable to log in with Facebook email | Login failure | Account Access |
| 45 | `2128551:2128551:2128550` | Why do you keep removing songs from certain albums | Catalog removals / licensing | Content Availability |
| 46 | `1574837:1574837:1574836` | Family account invite not sending / being received | Family plan invitation issue | Subscription & Plans |
| 47 | `2704314:2704314:2704312` | If I cancel trial now, does Premium continue until paid date? | Cancellation policy inquiry | Billing & Payments |
| 48 | `794159:794159:794158` | Cannot change password, contact form requires login | Password recovery loop | Account Access |
| 49 | `2707747:2707747:2707746` | Requesting Taylor Swift 'reputation' album release | Music release inquiry | Content Availability |
| 50 | `2125277:2125277:2125276` | Error message on everything tried to play, nothing works | Critical playback breakdown | Technical Support |

---

## 3. Core Recurring Issue Clusters & Frequencies in Dev Set
1. **Technical Support & App Glitches (7 cases, 14%)**:
   - Audio playback failures, tracks stuck or muted (`#21`, `#50`).
   - Sync and caching issues (`#37`).
   - App update regressions (`#36`).
   - Mobile and web player glitches (`#4`, `#26`, `#39`).
2. **Account Access & Security (5 cases, 10%)**:
   - Facebook SSO account disconnection / deletion lockout (`#22`, `#43`, `#44`).
   - Compromised or hacked accounts (`#23`).
   - Password reset loops and contact wall blocks (`#48`).
3. **Billing, Payments & Invoicing (6 cases, 12%)**:
   - Unexpected charges or billing disputes (`#9`).
   - Payment method renewal frequency (`#6`).
   - Paid for Premium but still showing Free tier (`#25`).
   - Payment timing vs paycheck (`#11`).
   - Grace period / payment extension requests (`#34`).
   - Cancellation and trial billing rules (`#47`).
4. **Subscription & Plan Administration (5 cases, 10%)**:
   - Family plan invite delivery failure (`#46`).
   - Family plan concurrent stream conflicts (`#32`).
   - Family plan account recovery (`#10`).
   - Account settings: address / country change limitations (`#42`).
   - Account closure / deletion requests (`#24`).
5. **Content Availability & Licensing (4 cases, 8%)**:
   - Specific tracks/albums missing in specific countries (`#1`, `#14`).
   - Catalog removal inquiries (`#45`).
   - Upcoming album release requests (`#49`).
6. **Platform Compatibility & Regional Rollout (7 cases, 14%)**:
   - Country availability & launch dates: India, Iraq, South Africa (`#8`, `#15`, `#27`, `#31`).
   - International usage limitations: Dubai travel restrictions (`#40`).
   - Device/Assistant integrations: Sonos voice, Siri, Apple Watch, Windows UWP (`#2`, `#12`, `#20`).
7. **Product Feedback & User Experience (8 cases, 16%)**:
   - Recommendation algorithm feedback (`#3`, `#38`).
   - Feature requests: "most played" filter, airplane mode detection (`#7`, `#28`).
   - Ad frequency and placement complaints (`#19`).
   - Free tier limitations complaint (`#41`).
   - Public metric / listener display requests (`#17`).
8. **Other, Banter, Praise & Ambiguous (8 cases, 16%)**:
   - Compliments and praise (`#13`).
   - Social banter / jokes (`#29`).
   - Incomplete / uninterpretable media-dependent exclamations (`#5`, `#35`).
   - Pop culture / artist fandom commentary (`#30`).
   - Meta support tweets (`#18`).
   - Solicitation of free perks (`#33`).
   - Vague hashtag queries (`#16`).
