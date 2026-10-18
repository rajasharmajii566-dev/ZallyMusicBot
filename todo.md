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

## Phase C: Make YouTube the preferred source ✅
- [x] `FALLBACK_HEAD_START=30` — YouTube (proxy) gets a head start; SoundCloud may only win after
- [x] SoundCloud kept strictly as a safety net
- [x] Verified: YouTube wins for kJQP7kiw5Fk (14.0 s), BddP6PYo2gs (15.6 s), Umqb9KENgmk (36.7 s)

## Phase D: Speed tuning ✅
- [x] Speed-ranked pool: `_probe_speed` measures real googlevideo throughput; pool sorted fastest-first
- [x] Winner-speed feedback stored so the pool keeps improving
- [x] Smaller m4a audio track preferred (fewer bytes for a slow proxy)
- [x] Parallel race of the 4 fastest proxies (first to finish wins)
- [x] Fail-fast timeouts + block memory + download cache
- [x] Tested aria2c multi-connection (1.8x on a good proxy) — off by default (too flaky on free proxies), single-connection retry kept as safety
- [x] Dockerfile installs aria2 (option available via `ARIA2_CONNECTIONS`)

## Phase E: Links ✅
- [x] config.py SUPPORT_CHANNEL / SUPPORT_CHAT -> https://t.me/rajamods7_ontop
- [x] userbot.py join_chat x5 -> rajamods7_ontop
- [x] .env + .env.example updated

## Phase F: Verify + ship ✅
- [x] End-to-end tests: YouTube audio + real YouTube MP4 (/vplay)
- [x] LIVE Telegram request -> real YouTube MP4 (`kfdplJ49_f0`, proxy @ 410 KB/s)
- [x] Temp test scripts deleted
- [x] FIXES.md / README.md / .env.example updated
- [x] Committed + pushed to GitHub (e9567a6, 2a6d70a)
- [x] Bot restarted and ON (PID 9274)
- [x] Report to user (they will deploy to Railway)
