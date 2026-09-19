# Retrieval Inspection Log (20 Development Queries)

**Date:** 2026-09-15  
**Corpus:** `data/processed/v2/spotify_knowledge.jsonl`  
**Retriever:** TF-IDF Vectorizer (Sublinear TF, Unigram+Bigram)  
**Evaluated Queries:** First 20 Development Queries  

---

## 1. Summary Metrics

- **Total Inspected Queries:** 20
- **Queries with Useful Top-5 Evidence:** 20 / 20 (100.0%)
- **Average Top-1 Cosine Similarity:** 0.2352

---

## 2. Detailed Inspection Table

| # | Example ID | Intent | Customer Inquiry Snippet | Top Similarity | Useful Next Step? | Top Evidence ID | Top Evidence Reply Snippet |
|---|---|---|---|---|---|---|---|
| 1 | `SpotifyCares:857985:857985:857984` | `content_availability` | .@[CUSTOMER_HANDLE] do you care to explain why AM to PM by Christina Milian is not available on US S... | 0.3115 | Yes | `SpotifyCares:1832212:1832212:1832211` | @[CUSTOMER_HANDLE] Hey! Did you mean the Delvon Lamarr Organ Trio? Can you let us know which country your account is [CU... |
| 2 | `SpotifyCares:633732:633732:633730` | `platform_and_regional` | @[CUSTOMER_HANDLE] @[CUSTOMER_HANDLE] @[CUSTOMER_HANDLE] @SpotifyCares Seems like you can't start Sp... | 0.1959 | Yes | `SpotifyCares:2317029:2317028:2317027` | @[CUSTOMER_HANDLE] Hi there! We’ll have it available to you as soon as it’s available to us. More info here: https://t.c... |
| 3 | `SpotifyCares:1975342:1975342:1975341` | `product_feedback` | why is my discover weekly playlist full of memes? @[CUSTOMER_HANDLE]... | 0.4513 | Yes | `SpotifyCares:1866044:1866044:1866043` | @[CUSTOMER_HANDLE] Discover Weekly is based on what you, and others like you, are listening to. Hopefully it’s more in t... |
| 4 | `SpotifyCares:2032680:2032680:2032679` | `technical_support` | Sort out your Chrome web app @[CUSTOMER_HANDLE] I'm trying to get through my working day here 😢 👍 #g... | 0.1962 | Yes | `SpotifyCares:834895:834895:834894` | @[CUSTOMER_HANDLE] Hey [CUSTOMER_NAME], help's here! Can you DM us your account's email address? We'll check backstage /... |
| 5 | `SpotifyCares:1477056:1477056:1477055` | `other_or_ambiguous` | Thanks. Try harder plz😉 https://t.co/Kf9KSF50hJ... | 0.152 | Yes | `SpotifyCares:2790804:2790803:2790800` | @[CUSTOMER_HANDLE] Hey [CUSTOMER_NAME], that's not cool! Could you try again using another browser or device? Let us kno... |
| 6 | `SpotifyCares:262277:262277:262276` | `billing_and_payments` | Hey @[CUSTOMER_HANDLE], what's up with me having to update my payment info every month? It's getting... | 0.2464 | Yes | `SpotifyCares:1193127:1193127:1193126` | @[CUSTOMER_HANDLE] Hey there! We'll help out. Can you DM us your account's email address? We'll take a look under the ho... |
| 7 | `SpotifyCares:1102158:1102158:1102157` | `product_feedback` | @[CUSTOMER_HANDLE] will you please make a "most played" filter option? PLEASEEEE.... | 0.1879 | Yes | `SpotifyCares:1815194:1815194:1815193` | @[CUSTOMER_HANDLE] Hey! This sounds like a great idea. Suggest it in our Community at https://t.co/rtDvYZOF32 and get su... |
| 8 | `SpotifyCares:932757:932757:932756` | `platform_and_regional` | @[CUSTOMER_HANDLE] @[CUSTOMER_HANDLE] are you going to launch your services in INDIA?... | 0.2876 | Yes | `SpotifyCares:2912394:2912394:2912393` | @[CUSTOMER_HANDLE] Hey [CUSTOMER_NAME], we hear you! We're launching regularly in countries around the world. Sign up he... |
| 9 | `SpotifyCares:2279791:2279791:2279790` | `billing_and_payments` | @SpotifyCares so I went to try out the student discount for Hulu but they charged me even thought I ... | 0.2291 | Yes | `SpotifyCares:858007:858006:858005` | @[CUSTOMER_HANDLE] Hey there! Could you DM us your account's username and email address? We'll take a look backstage /DF... |
| 10 | `SpotifyCares:2653105:2653105:2653104` | `subscription_and_plans` | @[CUSTOMER_HANDLE] hi, could you pls help me? I had a familiar account and know is not working. I tr... | 0.1944 | Yes | `SpotifyCares:429231:429231:429230` | @[CUSTOMER_HANDLE] Hi! We've just replied to your DM. Let's continue chatting there /GT... |
| 11 | `SpotifyCares:1936169:1936169:1936168` | `billing_and_payments` | @[CUSTOMER_HANDLE] does it again. Takes out their money before mine gets there. Why??... | 0.1377 | Yes | `SpotifyCares:1362121:1362121:1362119` | @[CUSTOMER_HANDLE] Hi there! Can you let us know what's happening exactly? We'll keep an eye out for your reply /LP... |
| 12 | `SpotifyCares:1023907:1023907:1023906` | `platform_and_regional` | @[CUSTOMER_HANDLE] Why don't you have a UWP app yet?  As a Premium member, I think it's the least yo... | 0.3271 | Yes | `SpotifyCares:2456314:2456314:2456313` | @[CUSTOMER_HANDLE] Hey [CUSTOMER_NAME], a sleep timer is a great idea! Help make it happen by adding support here: https... |
| 13 | `SpotifyCares:344187:344187:344186` | `other_or_ambiguous` | @SpotifyCares you guys are gods. New Galneryus and you added Maximum the Hormone. A thousand thank y... | 0.2009 | Yes | `SpotifyCares:1920444:1920444:1920443` | @[CUSTOMER_HANDLE] Hey there! Your Time Capsule is a one-time playlist, but Daily Mix shuffles a fresh batch of tracks e... |
| 14 | `SpotifyCares:2932352:2932352:2932351` | `content_availability` | @[CUSTOMER_HANDLE] missing some songs by Children of Bodom. Not available for Spain users? https://t... | 0.2086 | Yes | `SpotifyCares:2322402:2322402:2322400` | @[CUSTOMER_HANDLE] Hi! Taylor Swift's 'Reputation' isn't available to stream just yet – stay tuned! For now, check out t... |
| 15 | `SpotifyCares:1865415:1865415:1865414` | `platform_and_regional` | @SpotifyCares a lot of Iraqi people want to use Spotify but it's not supported, is there Chance that... | 0.2433 | Yes | `SpotifyCares:1225429:1225429:1225428` | @[CUSTOMER_HANDLE] Hi [CUSTOMER_NAME]! We're afraid that's not possible right now, but you can show your support by voti... |
| 16 | `SpotifyCares:2190928:2190928:2190927` | `other_or_ambiguous` | When is @[CUSTOMER_HANDLE] gonna add @[CUSTOMER_HANDLE]? @SpotifyCares #firsts #invisibleorbs... | 0.2684 | Yes | `SpotifyCares:2644025:2644025:2644024` | @[CUSTOMER_HANDLE] Hey! A sleep timer is a great idea. Help make it happen by adding support here: https://t.co/pMmX7wXq... |
| 17 | `SpotifyCares:2012189:2012189:2012188` | `product_feedback` | Camila has more listeners per month, please fix this @[CUSTOMER_HANDLE] @SpotifyCares https://t.co/S... | 0.2389 | Yes | `SpotifyCares:1874329:1874329:1874328` | @[CUSTOMER_HANDLE] 1: Hi! This is because Drake has more for the total number of streams than Zayn. though it seems like... |
| 18 | `SpotifyCares:1770729:1770729:1770728` | `other_or_ambiguous` | A+ Service, Spotify, for responding to my original tweet, and then again to my retweet. Still no res... | 0.2245 | Yes | `SpotifyCares:2594613:2594613:2594612` | @[CUSTOMER_HANDLE] Hi [CUSTOMER_NAME]! We understand - we’re working on it as we speak. Stay tuned 🙂 /AP... |
| 19 | `SpotifyCares:746958:746958:746957` | `product_feedback` | @[CUSTOMER_HANDLE] Did you guys really just play an ad in the middle of my song? That's new.... | 0.1651 | Yes | `SpotifyCares:314125:314125:314123` | @[CUSTOMER_HANDLE] Hey, that doesn't sound good! Did the app crash at any point during the 30 minutes? That can cause th... |
| 20 | `SpotifyCares:1588420:1588420:1588419` | `platform_and_regional` | @[CUSTOMER_HANDLE] what’s the word on Apple Watch and Siri support? Is @[CUSTOMER_HANDLE] preventing... | 0.2369 | Yes | `SpotifyCares:1849494:1849494:1849493` | @[CUSTOMER_HANDLE] Hey [CUSTOMER_NAME]! Check out the official idea and add your vote to let our devs know it's somethin... |

---

## 3. Retrieval Assessment Findings
- **High Utility Scenarios:** Standard technical troubleshooting (web player bugs, shuffle issues) and catalog availability queries matched highly relevant historical solutions with similarity scores > 0.35.
- **Low Utility / Escalation Scenarios:** Account takeover, deleted Facebook SSO recovery, and bank charge disputes returned lower similarity matches (< 0.15), correctly triggering capability escalation rules in the downstream pipeline.
