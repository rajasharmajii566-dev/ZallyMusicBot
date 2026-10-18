# ZallyMusicBot — Round 4: Make songs ACTUALLY play (no cookies needed)

## Phase A: Re-diagnose current state ✅
- [x] Confirm current sandbox IP still blocked by YouTube (52.12.117.99: dQw4w9WgXcQ OK, jNQXAC9IVRw / kJQP7kiw5Fk / BddP6PYo2gs = LOGIN_REQUIRED)
- [x] Check partial block: yes — a few videos work, most do not
- [x] Confirm error originates from a datacenter IP, not a code bug

## Phase B: Find a working alternative source ✅
- [x] Test Invidious instances — all 403/502/404 (they are on datacenter IPs too)
- [x] Test Piped instances — all 403/500/502
- [x] Test JioSaavn public APIs — all dead (DNS/404/402)
- [x] Test iTunes Search API — works (artwork only)
- [x] Test YouTube oEmbed — WORKS (title + thumbnail even while player API is blocked)
- [x] Test SoundCloud via yt-dlp — WORKS (search + download, some DRM tracks)
- [x] Test free public proxies — 10/120 reach YouTube, ~80% of those extract blocked videos
- [x] Pick: proxy pool (exact YouTube audio) + SoundCloud (fast, title matched)

## Phase C: Implement multi-source fallback ✅
- [x] New `PritiMusic/platforms/ytfallback.py`
- [x] ProxyPool: 6 list sources, latency sort, reachability test (50 threads), deep test on a blocked video, cache + rotate
- [x] SoundCloud fallback: oEmbed title -> clean_query -> scsearch -> relevance guard
- [x] Unicode folding so `Brahmāstra` == `Brahmastra`
- [x] Variant penalty (remix/cover/slowed/8d/karaoke/...) so the original wins
- [x] Still-image video (thumbnail + audio -> h264/aac mp4) for /vplay
- [x] Parallel race: first usable file wins (FALLBACK_HEAD_START, default 0)
- [x] Wire into `ytdlp_download()` so /play, /vplay, /song never die
- [x] Warm the pool at startup in `__main__.py`
- [x] Cookies / YT_PROXY still tried first when configured

## Phase D: Verify end-to-end ✅
- [x] `ytdlp_download("BddP6PYo2gs")` blocked -> mp3 6.78 MB, 192 kbps, 16 s
- [x] `ytdlp_download("9bZkp7q19f0", video=True)` blocked -> mp4 5.97 MB, h264+aac, 27 s
- [x] `ytdlp_download("kJQP7kiw5Fk")` blocked -> mp3 6.76 MB via proxy 41.216.186.161:8080
- [x] Proxy pool scan -> 11 working proxies in 196 s
- [x] SoundCloud match -> `Kesariya - Brahmastra` (sim 1.00) beats remix/cover
- [x] LIVE Telegram request -> `F2m4HPLvj-4` (/vplay, "Jaiye Sajana") -> mp4 4.76 MB, h264+aac, 181 s, 24 s total
- [x] Bot boots fully and stays running (PID 3239)

## Phase E: Deliver ✅
- [x] Commit `b570177` + push to GitHub main
- [x] Update FIXES.md (Round 4), README.md, .env.example, .gitignore
- [x] Bot restarted and ON
- [x] Summary to user
