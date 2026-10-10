# Task: Fix /vplay TypeError (music + video)

## Steps
- [x] Reproduce & find root cause (TypeError on /vplay)
- [x] Fix missing cookie_args() helper in Youtube.py
- [x] Wire yt-dlp fallback into download() (video + audio + song)
- [x] Guard None media path in call.py join_call
- [x] Test download(video=True/False) → h264 mp4 + mp3
- [x] Test full join_call(video=True) → JOIN_OK
- [x] Restart bot with fixes
- [x] Commit + push to GitHub
- [x] Update FIXES.md
