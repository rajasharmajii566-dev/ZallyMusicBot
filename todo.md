# ZallyMusicBot — Round 5: YouTube as source + faster + new links

User asks (Hinglish):
(a) "youtube se bhi song chale" — songs must actually come from YouTube
(b) support + updates links -> https://t.me/rajamods7_ontop
(c) "fast chalne chaiye song bhaut late find karta hai" — make it fast

## Phase A: Diagnose ✅
- [x] Confirm search is fast (0.5–1.1 s via py_yt) — NOT the bottleneck
- [x] Confirm YouTube-proxy download is slow (75–90 s via free proxies)
- [x] Confirm SoundCloud download is fast (6.5–9 s)
- [x] **Found the real bug**: `_try_proxies` wrapped `loop.run_in_executor(...)` (a Future) in `asyncio.create_task()` -> TypeError -> the whole YouTube-proxy path silently died, so SoundCloud always won

## Phase B: Fix the YouTube-proxy path ✅
- [x] Use the executor Future directly (asyncio.wait accepts futures)
- [x] Verified: proxy path now downloads the exact YouTube audio (kJQP7kiw5Fk, 6.76 MB)

## Phase C: Make YouTube the preferred source
- [ ] Add a source preference so YouTube (proxy) wins when it works
- [ ] Give the proxy path a configurable head start over SoundCloud
- [ ] Keep SoundCloud strictly as a fallback (never silently preferred)

## Phase D: Speed tuning
- [ ] Test aria2c multi-connection through a proxy (does it beat single-conn?)
- [ ] Add a bandwidth test to the pool so fast proxies are preferred
- [ ] Bound the worst case so a song never waits minutes

## Phase E: Links ✅
- [x] config.py SUPPORT_CHANNEL / SUPPORT_CHAT -> https://t.me/rajamods7_ontop
- [x] userbot.py join_chat x5 -> rajamods7_ontop
- [x] .env + .env.example updated

## Phase F: Verify + ship
- [ ] End-to-end test (YouTube wins, correct track, reasonable time)
- [ ] Delete temp test scripts
- [ ] Update FIXES.md / README.md / .env.example
- [ ] Commit + push to GitHub
- [ ] Restart bot ON
- [ ] Report to user (they will deploy to Railway)
