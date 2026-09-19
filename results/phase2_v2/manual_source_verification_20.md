# Manual Source ID Verification: 20 Reconstructed Development Conversations

**Audit Date:** 2026-09-14
**Source Database:** `data/cache/twcs_index.sqlite` (2,811,774 validated rows)
**Dataset Version:** Phase 2 v2 (Frozen)

This document audits the first 20 reconstructed development conversations against the raw source SQLite database records. It verifies:

1. **Customer Target Identity:** Exists in DB, `inbound == 1`, `author_id != 'SpotifyCares'`, matches text.
2. **Brand Reply Reference:** Exists in DB, `inbound == 0`, `author_id == 'SpotifyCares'`, `in_response_to_tweet_id == target_customer_tweet_id`.
3. **Thread Ancestor Chain:** All ancestor turns match parent links backward to conversation root.
4. **Future Reply Isolation:** The brand reply and any subsequent turns are verified absent from model input text.

---

## [01/20] Example `SpotifyCares:857985:857985:857984` (Group `857985`)
- **Target Customer Tweet ID**: `857985`
  - DB Raw Author: `323746` | Inbound: `1`
  - Created At: `Thu Oct 19 15:48:50 +0000 2017`
  - Raw DB Text: `.@115888 do you care to explain why AM to PM by Christina Milian is not available on US Spotify?!?`
- **Selected Brand Reply Tweet ID**: `857984`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `857985` (Matches Customer: `True`)
  - Raw DB Reply: `@323746 Hey there, help's here! Are you getting any error messages when trying to play the song? Keep us in the loop /KL`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `857984` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [02/20] Example `SpotifyCares:633732:633732:633730` (Group `633732`)
- **Target Customer Tweet ID**: `633732`
  - DB Raw Author: `270215` | Inbound: `1`
  - Created At: `Wed Oct 04 16:47:22 +0000 2017`
  - Raw DB Text: `@118117 @137949 @115888 @SpotifyCares Seems like you can't start Spotify music/playlists with new Sonos voice control.  What gives?`
- **Selected Brand Reply Tweet ID**: `633730`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `633732` (Matches Customer: `True`)
  - Raw DB Reply: `@270215 Hey Lee, help's here! This isn't currently possible. We'll be sure to pass on your feedback 🙂 /CG`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `633730` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [03/20] Example `SpotifyCares:1975342:1975342:1975341` (Group `1975342`)
- **Target Customer Tweet ID**: `1975342`
  - DB Raw Author: `584975` | Inbound: `1`
  - Created At: `Wed Nov 01 15:01:58 +0000 2017`
  - Raw DB Text: `why is my discover weekly playlist full of memes? @115888`
- **Selected Brand Reply Tweet ID**: `1975341`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1975342` (Matches Customer: `True`)
  - Raw DB Reply: `@584975 Hi there! Can you tell us more about it? We'd like to take a closer look on this one. If you can send a screenshot, that'd be handy /XF`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1975341` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [04/20] Example `SpotifyCares:2032680:2032680:2032679` (Group `2032680`)
- **Target Customer Tweet ID**: `2032680`
  - DB Raw Author: `601074` | Inbound: `1`
  - Created At: `Tue Nov 07 15:05:07 +0000 2017`
  - Raw DB Text: `Sort out your Chrome web app @115888 I'm trying to get through my working day here 😢 👍 #glitchy`
- **Selected Brand Reply Tweet ID**: `2032679`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `2032680` (Matches Customer: `True`)
  - Raw DB Reply: `@601074 Hey Andy! Does clearing your cache/cookies help? You might also want to try using an incognito window. Let us know how it goes /KL`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `2032679` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [05/20] Example `SpotifyCares:1477056:1477056:1477055` (Group `1477056`)
- **Target Customer Tweet ID**: `1477056`
  - DB Raw Author: `462673` | Inbound: `1`
  - Created At: `Thu Nov 02 22:44:32 +0000 2017`
  - Raw DB Text: `Thanks. Try harder plz😉 https://t.co/Kf9KSF50hJ`
- **Selected Brand Reply Tweet ID**: `1477055`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1477056` (Matches Customer: `True`)
  - Raw DB Reply: `@462673 You're welcome. Thanks for sharing your feedback, we'll pass it on to the relevant folks /SY`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1477055` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [06/20] Example `SpotifyCares:262277:262277:262276` (Group `262277`)
- **Target Customer Tweet ID**: `262277`
  - DB Raw Author: `178474` | Inbound: `1`
  - Created At: `Thu Oct 05 20:43:18 +0000 2017`
  - Raw DB Text: `Hey @115888, what's up with me having to update my payment info every month? It's getting annoying.`
- **Selected Brand Reply Tweet ID**: `262276`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `262277` (Matches Customer: `True`)
  - Raw DB Reply: `@178474 Hi there. Can you DM us your account's email address? We'll take a look backstage /LM https://t.co/ldFdZRiNAt`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `262276` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [07/20] Example `SpotifyCares:1102158:1102158:1102157` (Group `1102158`)
- **Target Customer Tweet ID**: `1102158`
  - DB Raw Author: `380067` | Inbound: `1`
  - Created At: `Mon Oct 23 21:26:05 +0000 2017`
  - Raw DB Text: `@115888 will you please make a "most played" filter option? PLEASEEEE.`
- **Selected Brand Reply Tweet ID**: `1102157`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1102158` (Matches Customer: `True`)
  - Raw DB Reply: `@380067 Hey! We hear you 🎧 Rest assured your feedback will be passed on to the right folks /DF`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1102157` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [08/20] Example `SpotifyCares:932757:932757:932756` (Group `932757`)
- **Target Customer Tweet ID**: `932757`
  - DB Raw Author: `341254` | Inbound: `1`
  - Created At: `Sat Oct 21 10:08:37 +0000 2017`
  - Raw DB Text: `@115888 @61267 are you going to launch your services in INDIA?`
- **Selected Brand Reply Tweet ID**: `932756`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `932757` (Matches Customer: `True`)
  - Raw DB Reply: `@341254 Hey Yogesh! We're launching in new countries as often as possible. Be sure to add your email at https://t.co/X8DVSX9QgM /BP`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `932756` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [09/20] Example `SpotifyCares:2279791:2279791:2279790` (Group `2279791`)
- **Target Customer Tweet ID**: `2279791`
  - DB Raw Author: `662784` | Inbound: `1`
  - Created At: `Sat Nov 11 16:50:48 +0000 2017`
  - Raw DB Text: `@SpotifyCares so I went to try out the student discount for Hulu but they charged me even thought I didn’t sign up for it after all what’s going on??`
- **Selected Brand Reply Tweet ID**: `2279790`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `2279791` (Matches Customer: `True`)
  - Raw DB Reply: `@662784 Hey! That doesn't sound good. Could you DM us your account's email address? We'll take a look backstage /AU https://t.co/ldFdZRiNAt`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `2279790` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [10/20] Example `SpotifyCares:2653105:2653105:2653104` (Group `2653105`)
- **Target Customer Tweet ID**: `2653105`
  - DB Raw Author: `748214` | Inbound: `1`
  - Created At: `Sun Nov 19 04:46:08 +0000 2017`
  - Raw DB Text: `@115888 hi, could you pls help me? I had a familiar account and know is not working. I tried to got it back but I couldn’t`
- **Selected Brand Reply Tweet ID**: `2653104`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `2653105` (Matches Customer: `True`)
  - Raw DB Reply: `@748214 Hi there! Help's here. Can you DM us your account's email address or username? We'll take a look backstage /NQ`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `2653104` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [11/20] Example `SpotifyCares:1936169:1936169:1936168` (Group `1936169`)
- **Target Customer Tweet ID**: `1936169`
  - DB Raw Author: `576042` | Inbound: `1`
  - Created At: `Fri Oct 27 21:23:50 +0000 2017`
  - Raw DB Text: `@115888 does it again. Takes out their money before mine gets there. Why??`
- **Selected Brand Reply Tweet ID**: `1936168`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1936169` (Matches Customer: `True`)
  - Raw DB Reply: `@576042 Hey John, help's here! Could you send us a DM with your account's email address or username? We'll take a look backstage /CO https://t.co/ldFdZRiNAt`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1936168` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [12/20] Example `SpotifyCares:1023907:1023907:1023906` (Group `1023907`)
- **Target Customer Tweet ID**: `1023907`
  - DB Raw Author: `362304` | Inbound: `1`
  - Created At: `Sun Oct 22 17:22:35 +0000 2017`
  - Raw DB Text: `@115888 Why don't you have a UWP app yet?  As a Premium member, I think it's the least you can do.`
- **Selected Brand Reply Tweet ID**: `1023906`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1023907` (Matches Customer: `True`)
  - Raw DB Reply: `@362304 Hey! You can show your support for this idea by voting for it here: https://t.co/TGZFKt4dIg /NQ`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1023906` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [13/20] Example `SpotifyCares:344187:344187:344186` (Group `344187`)
- **Target Customer Tweet ID**: `344187`
  - DB Raw Author: `197858` | Inbound: `1`
  - Created At: `Sun Oct 08 01:18:39 +0000 2017`
  - Raw DB Text: `@SpotifyCares you guys are gods. New Galneryus and you added Maximum the Hormone. A thousand thank yous`
- **Selected Brand Reply Tweet ID**: `344186`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `344187` (Matches Customer: `True`)
  - Raw DB Reply: `@197858 Hey, you're welcome! Let us know if you need anything else. Happy listening 🎧 /RK`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `344186` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [14/20] Example `SpotifyCares:2932352:2932352:2932351` (Group `2932352`)
- **Target Customer Tweet ID**: `2932352`
  - DB Raw Author: `810988` | Inbound: `1`
  - Created At: `Wed Nov 29 08:16:22 +0000 2017`
  - Raw DB Text: `@115888 missing some songs by Children of Bodom. Not available for Spain users? https://t.co/0j4hITXVQd`
- **Selected Brand Reply Tweet ID**: `2932351`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `2932352` (Matches Customer: `True`)
  - Raw DB Reply: `@810988 Hey Alberto! We’d love to have all of their stuff available in all territories, but we have some info about content here: https://t.co/1dgftcFtzc. Hope this info helps /GK`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `2932351` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [15/20] Example `SpotifyCares:1865415:1865415:1865414` (Group `1865415`)
- **Target Customer Tweet ID**: `1865415`
  - DB Raw Author: `557307` | Inbound: `1`
  - Created At: `Fri Oct 20 15:22:45 +0000 2017`
  - Raw DB Text: `@SpotifyCares a lot of Iraqi people want to use Spotify but it's not supported, is there Chance that be supported in Iraq ?`
- **Selected Brand Reply Tweet ID**: `1865414`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1865415` (Matches Customer: `True`)
  - Raw DB Reply: `@557307 Hey there! We're launching regularly in countries around the world. Sign up here to be first to hear: https://t.co/XDwWzj7cLP /AG`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1865414` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [16/20] Example `SpotifyCares:2190928:2190928:2190927` (Group `2190928`)
- **Target Customer Tweet ID**: `2190928`
  - DB Raw Author: `641341` | Inbound: `1`
  - Created At: `Thu Nov 09 18:15:48 +0000 2017`
  - Raw DB Text: `When is @115888 gonna add @86685? @SpotifyCares #firsts #invisibleorbs`
- **Selected Brand Reply Tweet ID**: `2190927`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `2190928` (Matches Customer: `True`)
  - Raw DB Reply: `@641341 Hey there! We'd love to have them on Spotify! Hopefully we will in the future. Check this out: https://t.co/MEjmIRL2eB /JX`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `2190927` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [17/20] Example `SpotifyCares:2012189:2012189:2012188` (Group `2012189`)
- **Target Customer Tweet ID**: `2012189`
  - DB Raw Author: `594996` | Inbound: `1`
  - Created At: `Sun Nov 05 11:32:19 +0000 2017`
  - Raw DB Text: `Camila has more listeners per month, please fix this @115888 @SpotifyCares https://t.co/ScG3I5Z3cG`
- **Selected Brand Reply Tweet ID**: `2012188`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `2012189` (Matches Customer: `True`)
  - Raw DB Reply: `@594996 Hi! Sorry you feel that way. It can take some time for the rankings to update. All changes will reflect correctly as our systems update /RE`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `2012188` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [18/20] Example `SpotifyCares:1770729:1770729:1770728` (Group `1770729`)
- **Target Customer Tweet ID**: `1770729`
  - DB Raw Author: `532309` | Inbound: `1`
  - Created At: `Wed Nov 08 00:38:30 +0000 2017`
  - Raw DB Text: `A+ Service, Spotify, for responding to my original tweet, and then again to my retweet. Still no response from @188 https://t.co/qHWLyopb3t`
- **Selected Brand Reply Tweet ID**: `1770728`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1770729` (Matches Customer: `True`)
  - Raw DB Reply: `@532309 If you could DM us the link to your Facebook profile page, we'll see what we can dig up /AN https://t.co/ldFdZRiNAt`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1770728` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [19/20] Example `SpotifyCares:746958:746958:746957` (Group `746958`)
- **Target Customer Tweet ID**: `746958`
  - DB Raw Author: `298570` | Inbound: `1`
  - Created At: `Wed Oct 11 16:31:11 +0000 2017`
  - Raw DB Text: `@115888 Did you guys really just play an ad in the middle of my song? That's new.`
- **Selected Brand Reply Tweet ID**: `746957`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `746958` (Matches Customer: `True`)
  - Raw DB Reply: `@298570 Hey there! That's not cool. Does logging out &gt; restarting the device &gt; logging back in help? Keep us posted /KL`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `746957` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

## [20/20] Example `SpotifyCares:1588420:1588420:1588419` (Group `1588420`)
- **Target Customer Tweet ID**: `1588420`
  - DB Raw Author: `488504` | Inbound: `1`
  - Created At: `Sat Nov 04 15:38:05 +0000 2017`
  - Raw DB Text: `@115888 what’s the word on Apple Watch and Siri support? Is @115858 preventing this  or are you slow to the game?`
- **Selected Brand Reply Tweet ID**: `1588419`
  - DB Author: `SpotifyCares` | Outbound: `True`
  - Direct Parent in DB: `1588420` (Matches Customer: `True`)
  - Raw DB Reply: `@488504 Hey! Check out the official idea and add your vote to convince our devs it's something to look into: https://t.co/SEK4E4gi22 /DF`
- **Reconstructed Ancestor Chain Length**: `1` turns
  - Target is Final Turn in Input: `True`
  - Future Reply `1588419` Hidden from Model Input: `True`
- **Audit Status**: ✅ **VERIFIED SOURCE INTEGRITY PASS**

---

## Summary Audit Result
✅ **ALL 20 CONVERSATIONS 100% VERIFIED AGAINST SOURCE SQLITE DATABASE**
