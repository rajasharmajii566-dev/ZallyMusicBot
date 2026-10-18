# ZallyMusicBot Fix — Todo

## Phase 1: Recon & Environment  ✅
- [x] Inspect repo structure and download logic (Youtube.py)
- [x] Install ffmpeg + yt-dlp, verify Python env
- [x] Reproduce: audio + video download WORK from sandbox IP (AWS us-west-2)
- [x] Confirm block is IP-specific ("Sign in to confirm you're not a bot" on datacenter IPs)
- [x] Validate assistant STRING_SESSION (7809063450 / @Nglord910)
- [x] Boot bot successfully (Music Bot Started + Assistant + PyTgCalls)

## Phase 2: Diagnose the YouTube block  ✅
- [x] Determine cause: datacenter IP + missing cookies + missing JS runtime + no PO token
- [x] Confirm modern yt-dlp needs a JS runtime (node) + EJS challenge solver
- [x] Confirm failing videos return "visionos player response playability status: LOGIN_REQUIRED"
- [x] Confirm "PO Token Providers: none" (no token provider installed)

## Phase 3: Implement the fix  ✅
- [x] Harden yt-dlp options (js_runtimes node + remote_components ejs:github)
- [x] Multi-client retries (default → android → ios → web_safari → tv_embedded)
- [x] Robust cookie loading (file + COOKIES + COOKIES_BASE64 env)
- [x] Optional proxy support (YT_PROXY / YTDLP_PROXY / PROXY_URL)
- [x] Clearer error handling + actionable "add cookies" message
- [x] Pin yt-dlp>=2025.9.5 in requirements
- [x] cookies/ folder + README + .gitignore entry
- [x] Update README + .env.example

## Phase 4: Verify  ⏳
- [x] Unit-check: js_runtimes/remote_components/cookie_args wired correctly
- [ ] Direct download() test (audio mp3 + video h264 mp4) on a non-blocked video
- [ ] PO-token provider (bgutil) build + test — does it fix blocked videos?
- [ ] End-to-end /play test through Telegram (assistant sends command)
- [ ] Bot running & responsive

## Phase 5: Deliver  ⏳
- [ ] Commit & push fixes to GitHub
- [ ] Update FIXES.md
- [ ] Provide summary + run instructions
