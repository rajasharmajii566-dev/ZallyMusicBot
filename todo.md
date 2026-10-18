# ZallyMusicBot — Round 4: Make songs ACTUALLY play (no cookies needed)

## Phase A: Re-diagnose current state
- [ ] Confirm current sandbox IP still blocked by YouTube
- [ ] Check if IP changed / partial block (some videos work)
- [ ] Confirm error originates from my sandbox (not user's Railway)

## Phase B: Find a working alternative source
- [ ] Test Invidious instances (audio stream endpoint)
- [ ] Test Piped instances (streams API)
- [ ] Test JioSaavn / other music APIs (Hindi songs)
- [ ] Test free/public proxies with yt-dlp
- [ ] Pick the most reliable working source

## Phase C: Implement multi-source fallback in code
- [ ] Add fallback downloader chain in Youtube.py
- [ ] Wire it into download() so /play never dies on YT block
- [ ] Keep cookies/proxy as highest priority when present

## Phase D: Verify end-to-end
- [ ] Direct download test on a BLOCKED video -> file produced
- [ ] Bot boot + /play e2e
- [ ] Confirm audio plays (ffprobe duration/codec)

## Phase E: Deliver
- [ ] Commit & push to GitHub
- [ ] Restart bot ON
- [ ] Summary to user
