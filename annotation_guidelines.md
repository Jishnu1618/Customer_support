# Annotation Guidelines: Spotify Customer Support Reply Agent

**Document Version:** 1.0 (Frozen Specification)  
**Applicability:** Phase 2 v2 Development Inputs (50) & Evaluation Pool Samples (200)  
**Author:** Pair Programmer / Primary Human Annotator  

---

## 1. Objective & Guiding Principles

These guidelines define the operational criteria for annotating customer inquiries to the `@SpotifyCares` support account. The goal is to provide reliable gold labels for:
1. **Customer Intent Classification** (Categorizing customer needs into an 8-intent taxonomy).
2. **Actionable Routing & Safety Decisions** (Determining whether a safe automated reply can be generated vs. requiring escalation to a human specialist).
3. **Reply Governance** (Specifying mandatory reply elements, prohibited claims, and clarification requirements).

### Core Annotation Principles:
- **Strict Context Boundary:** Annotate solely from the customer's target inquiry and preceding conversation history. **Never use future replies or held-out agent responses to determine labels.**
- **Autonomous Safety vs. Total Resolution:** `auto_handle` means a safe, policy-compliant, helpful response can be sent autonomously by the bot—it does **not** mean the customer's underlying issue is guaranteed to be fully resolved in one turn.
- **Independence from Historical "DM us" Behavior:** Historical Spotify agents frequently used boilerplate "Send us a DM" tweets to move conversations to private channels. **A historical DM request is not an automatic escalation label.** Only escalate if the inquiry inherently requires private financial data, backend database edits, or human security authorization.

---

## 2. Intent Taxonomy (8 Mutually Exclusive Categories)

### 2.1 `content_availability` (Content Availability & Licensing)
- **Definition:** Questions regarding missing, removed, greyed out, or upcoming songs, albums, artists, or podcasts, including regional catalog differences.
- **Inclusions:**
  - Inquiring why a specific track/album/artist is unavailable in a particular country.
  - Inquiring why songs disappeared or were removed from existing albums/playlists.
  - Asking when an upcoming album/single will be released on Spotify.
- **Exclusions:**
  - Playback failure where the track exists and is listed but produces an error when clicking play (`technical_support`).
  - General availability of Spotify service across an entire country (`platform_and_regional`).
- **Development Examples:**
  - *“why AM to PM by Christina Milian is not available on US Spotify?!?”* (`857985`)
  - *“missing some songs by Children of Bodom. Not available for Spain users?”* (`2932352`)
  - *“why do you guys keep removing songs from certain albums”* (`2128551`)
  - *“put out #reputation on Spotify”* (`2707747`)

### 2.2 `technical_support` (Technical Support & App Performance)
- **Definition:** Issues involving software bugs, playback failures, crashes, audio glitches, sync problems, offline download failures, or UI rendering defects.
- **Inclusions:**
  - Audio failing to play, UI buttons pressing without sound, playback freezing or skipping.
  - Mobile, desktop, or web player crashes, freezes, or high resource usage.
  - Regressions or bugs introduced by recent app updates (e.g., song timestamps).
  - Sync delays across devices or desktop podcast feed refresh delays.
  - Visual layout bugs (e.g., text cutoff, incorrect song counts).
- **Exclusions:**
  - Playback stopping because another device on the same Family account started playing (`subscription_and_plans`).
  - Third-party voice assistant / smart speaker integration issues (`platform_and_regional`).
- **Development Examples:**
  - *“Sort out your Chrome web app @Spotify I'm trying to get through my working day here #glitchy”* (`2032680`)
  - *“tracks ive downloaded do not respond when I hit play. The GUI presses but no sound. Old stuff ok”* (`1837746`)
  - *“Too bad shuffle doesn’t work on mobile.”* (`2511299`)
  - *“recent update won’t let me switch songs without starting the next at the time stamp from the previous”* (`1949728`)
  - *“podcasts like take so long to show up in my Windows desktop player”* (`2198134`)
  - *“weird bug where the total amount of songs is cutoff”* (`749218`)
  - *“This message on everything I try to play. Nothing works. FAQs no help at all.”* (`2125277`)

### 2.3 `account_access` (Account Access & Security)
- **Definition:** Problems logging in, password resets, account takeover/compromise, or lockout following third-party SSO (e.g., Facebook) deletion.
- **Inclusions:**
  - Inability to log in, forgotten passwords, password reset links not arriving.
  - Account lockout after deleting or disconnecting a linked Facebook account.
  - Compromised, hacked, or stolen Spotify accounts.
  - Catch-22 support barriers (e.g., needing to log in to access the contact form).
- **Exclusions:**
  - Voluntarily requesting to permanently delete or close an account (`subscription_and_plans`).
  - Updating billing address or account profile information (`subscription_and_plans`).
- **Development Examples:**
  - *“deleted my Facebook account and now cannot access my spotify account. Help.”* (`2707737`)
  - *“hi my premium account has been hacked. How may I proceed from here? Thanks.”* (`689544`)
  - *“I deleted my Facebook account without realising my Spotify account was connected. Now I can't access my Spotify account”* (`617481`)
  - *“I am unable to log in. My Facebook account's e-mail address is [EMAIL_REDACTED] I have a Premium. Please help ASAP!”* (`1799988`)
  - *“I cant change my password and if I try to contact you; it makes me sign in, and I dont know my password”* (`794159`)

### 2.4 `billing_and_payments` (Billing, Payments & Invoicing)
- **Definition:** Disputes or questions regarding subscription charges, payment methods, billing dates, missing premium status, grace periods, or cancellation billing timing.
- **Inclusions:**
  - Unexpected or disputed charges (e.g., student bundle charges).
  - Frequent requests to update payment methods or payment failure notifications.
  - Premium service missing or showing "Free" despite successful payment deduction.
  - Billing deduction timing relative to salary/paychecks.
  - Requests for grace periods or billing extensions.
  - Inquiries about billing duration after cancelling a free trial.
- **Exclusions:**
  - Changing subscription plan tiers (e.g., upgrading to Family) (`subscription_and_plans`).
  - General complaints about premium pricing or ad frequency (`product_feedback`).
- **Development Examples:**
  - *“what's up with me having to update my payment info every month? It's getting annoying.”* (`262277`)
  - *“went to try out the student discount for Hulu but they charged me even thought I didn’t sign up for it”* (`2279791`)
  - *“Takes out their money before mine gets there. Why??”* (`1936169`)
  - *“hey I am getting charged for a premium account and I’m not getting the services of a premium account and it says I’m still on free?”* (`591479`)
  - *“can you grant me a grace period for my premium account??? i have a urgent matter”* (`38322`)
  - *“If I cancel the account now, will premium continue to work until the last day, payed for?”* (`2704314`)

### 2.5 `subscription_and_plans` (Subscription & Plan Management)
- **Definition:** Inquiries regarding Spotify plan types (Family, Student, Duo, Individual), Family member invitations, address verification, multi-stream rules, or account closure.
- **Inclusions:**
  - Family plan invite delivery issues or member onboarding failures.
  - Simultaneous playback stream cutoffs across Family plan members.
  - Account address/country update restrictions tied to subscription eligibility.
  - Requests to permanently delete or close an account.
  - Expired or disconnected Family plan membership recovery.
- **Exclusions:**
  - General login failures or forgotten passwords (`account_access`).
  - Direct disputes over unauthorized bank charges (`billing_and_payments`).
- **Development Examples:**
  - *“I had a familiar account and know is not working. I tried to got it back but I couldn’t”* (`2653105`)
  - *“i wanna delete my account, nobody wants that connected to facebook. give us an option to delete it”* (`576195`)
  - *“Why does my music keep getting cut off on my office pc when my wife listens to Spotify in the house? We are paying Premium for Family Acct.”* (`2766505`)
  - *“Why the heck I cannot change the address of my account??? Can you give me an straight answer??”* (`670016`)
  - *“my partner paid for a family account but I'm not receiving the invite! Nothing to do with email. It's not sending it. Help!”* (`1574837`)

### 2.6 `platform_and_regional` (Platform Compatibility & Regional Availability)
- **Definition:** Service availability in specific countries/regions, international roaming limits, or integration with external hardware/operating systems.
- **Inclusions:**
  - Inquiring when Spotify will launch in a country (e.g., India, Iraq, South Africa).
  - Travel and roaming listening restrictions (e.g., 14-day international limit).
  - External hardware or assistant integrations (Sonos voice control, Apple Watch, Siri, Windows UWP).
- **Exclusions:**
  - Availability of a specific song or artist in an active country (`content_availability`).
  - General app crashes on standard mobile/desktop apps (`technical_support`).
- **Development Examples:**
  - *“Seems like you can't start Spotify music/playlists with new Sonos voice control. What gives?”* (`633732`)
  - *“are you going to launch your services in INDIA?”* (`932757`)
  - *“Why don't you have a UWP app yet? As a Premium member, I think it's the least you can do.”* (`1023907`)
  - *“a lot of Iraqi people want to use Spotify but it's not supported, is there Chance that be supported in Iraq ?”* (`1865415`)
  - *“what’s the word on Apple Watch and Siri support? Is Apple preventing this or are you slow to the game?”* (`1588420`)
  - *“when you're coming to india?”* (`2375424`)
  - *“make the app available is south Africa plzzzzzz”* (`2572204`)
  - *“i can't even use my Spotify account in Dubai??? Guess I have to cancel and join Tidal or Apple Music.”* (`2158535`)

### 2.7 `product_feedback` (Product Feedback, Suggestions & UX Complaints)
- **Definition:** Feature suggestions, UI/UX feedback, comments on recommendation algorithms, ad frequency/placement complaints, or general user experience discontent.
- **Inclusions:**
  - Suggestions for new app features, filters, or offline controls (e.g., "most played" filter, airplane mode detection).
  - Complaints about algorithmic playlist selections (e.g., memes in Discover Weekly, unwanted recommended songs in user playlists).
  - Complaints regarding ad placement or ad frequency on free tier (e.g., ad playing mid-song).
  - Frustration with free tier feature constraints without asking for troubleshooting.
  - Public artist listener count or profile display requests.
- **Exclusions:**
  - Reproducible software bugs, crashes, or playback glitches (`technical_support`).
  - Missing song licensing requests (`content_availability`).
- **Development Examples:**
  - *“why is my discover weekly playlist full of memes? @Spotify”* (`1975342`)
  - *“will you please make a "most played" filter option? PLEASEEEE.”* (`1102158`)
  - *“Camila has more listeners per month, please fix this”* (`2012189`)
  - *“Did you guys really just play an ad in the middle of my song? That's new.”* (`746958`)
  - *“Kind of amazed how after all these years Spotify still doesn’t have an option for detecting airplane mode and showing downloaded music only.”* (`172468`)
  - *“Quit these recommended songs or at least add an option to turn them off.”* (`2191425`)
  - *“forced off of my premium. I don’t know if I want to buy it again if the free guys get shit on by greed”* (`1825353`)

### 2.8 `other_or_ambiguous` (Other, Social Banter & Ambiguous)
- **Definition:** Messages lacking an actionable support request, including compliments/praise, casual banter, jokes, vague or uninterpretable complaints requiring external media, fandom commentary, or spam.
- **Inclusions:**
  - Compliments, gratitude, or praise with no unresolved issue.
  - Social jokes, banter, or meta-questions (e.g., "what's a DM?").
  - Posts consisting only of links/screenshots with vague emotional expressions ("Please explain yourself!!").
  - Celebrity fandom spam or hashtags without an actionable user issue.
  - General solicitations for free premium perks or giveaways.
- **Exclusions:**
  - Messages with clear text describing an issue even if a link/image is attached (classify by the text).
- **Development Examples:**
  - *“Thanks. Try harder plz😉 https://t.co/Kf9KSF50hJ”* (`1477056`)
  - *“you guys are gods. New Galneryus and you added Maximum the Hormone. A thousand thank yous”* (`344187`)
  - *“When is @user gonna add @user? #firsts #invisibleorbs”* (`2190928`)
  - *“A+ Service, Spotify, for responding to my original tweet... Still no response from other brand”* (`1770729`)
  - *“hey what’s a DM 😂?”* (`754546`)
  - *“STOP SABOTAGING SELENA ON SPOTIFY SMH”* (`1281628`)
  - *“what can i do for you to give me free premium @SpotifyCares”* (`1629841`)
  - *“Please explain yourself!! why is this happening 😢 https://t.co/sLV9qZjs4N”* (`2028677`)

---

## 3. Multi-Intent Priority & Tie-Breaking Rules

When a customer inquiry touches multiple subjects, apply this strict precedence order:
1. **Security / Account Takeover (`account_access`):** Safety and credential security take precedence over any other issue.
2. **Direct Financial / Billing Disputes (`billing_and_payments`):** Active charges or payment failures take priority over plan settings.
3. **Reproducible Functional / Technical Failures (`technical_support`):** Broken playback or app crashes take priority over feedback or licensing questions.
4. **Subscription Tier / Family Management (`subscription_and_plans`):** Plan configurations take priority over general feature questions.
5. **Specific Content Availability (`content_availability`):** Specific song/artist inquiries take priority over general platform inquiries.
6. **Platform & Regional Compatibility (`platform_and_regional`):** Device/regional support questions take priority over general feedback.
7. **Product Feedback & Complaints (`product_feedback`):** Actionable suggestions take priority over ambiguous banter.
8. **Ambiguous / Banter (`other_or_ambiguous`):** Lowest precedence; only selected when no actionable category applies.

---

## 4. Routing Guidelines: Auto-Handle vs. Escalate

### 4.1 Safe Auto-Handle (`auto_handle`)
An inquiry should be routed to `auto_handle` when the agent can safely, accurately, and politely respond using standard knowledge, public troubleshooting steps, official policy explanations, or self-serve links.

**Typical Auto-Handle Scenarios:**
- **Standard Technical Troubleshooting:** Recommending a clean reinstall, clearing cache, checking offline toggle, testing on another connection, or requesting device/OS details.
- **Policy & Licensing Explanations:** Explaining that music availability depends on agreements with rights holders, explaining the 14-day travel rule, or explaining Family plan simultaneous streaming rules (separate accounts needed).
- **Self-Service Guidance:** Directing users to public self-serve tools (e.g., password reset portal, account overview page for invites, Spotify Community for feature votes).
- **Country Rollout Status:** Explaining that Spotify continuously works on expanding to new markets and pointing to the official newsroom/community.
- **Clarification Requests:** Asking the user for specific technical details (device, OS, app version) when necessary to proceed.
- **Feedback Acknowledgement & Polite Banter:** Thanking the user for compliments, acknowledging feedback, or politely declining free premium requests.

### 4.2 Mandatory Escalation (`escalate`)
An inquiry **must** be routed to `escalate` when resolving it requires confidential data, backend database mutations, internal billing lookups, or manual human policy exceptions.

**Mandatory Escalation Scenarios:**
- **Account Compromise / Security:** Account is hacked, email changed without consent, unauthorized activity detected.
- **Financial / Billing Disputes:** Unrecognized bank charges, dispute of recurring fees, double-charging, refund requests requiring financial transaction lookup.
- **SSO Disconnection / Lost Access:** Facebook account deleted/disabled where the user cannot authenticate via email/password and requires manual backend account recovery/migration.
- **Manual Account Overrides:** Inability to update country/address on the web portal requiring support agent backend override, or requests for billing grace periods/extensions.
- **Severe Complaints / Legal Threats:** Escalated threats of legal action or executive complaints.

---

## 5. Required Annotation Schema (10 Fields)

Every annotation record must contain the following 10 fields:

| Field Name | Type | Allowed Values / Format | Description |
|---|---|---|---|
| `example_id` | string | `SpotifyCares:<group_id>:<cust_id>:<reply_id>` | Unique composite ID from manifest |
| `intent` | string | One of the 8 defined intents | Primary classified intent |
| `handling_decision` | string | `auto_handle` or `escalate` | Operational routing decision |
| `handling_reason` | string | Controlled snake_case string | Specific rationale for routing decision (e.g., `standard_troubleshooting`, `licensing_explanation`, `requires_account_lookup`, `security_compromise`) |
| `required_reply_elements` | string | Semicolon-separated string | Mandatory information that a compliant response must include |
| `prohibited_claims_or_actions` | string | Semicolon-separated string | Information or promises the agent must never make |
| `needs_clarification` | boolean | `True` or `False` | Whether customer input lacks essential technical details |
| `annotation_confidence` | string | `high`, `medium`, `low` | Confidence of the human annotator |
| `annotator_id` | string | `human_annotator_1` | Identifier of the human annotator |
| `notes` | string | Free text | Specific observations, edge case explanations, or context notes |
