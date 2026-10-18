# ZallyMusicBot

Advanced Telegram music player bot built with Pyrogram (Kurigram) + Py-TgCalls.
Supports YouTube, Spotify, Apple Music, SoundCloud, Resso and Telegram audio/video,
with both **audio** and **video** voice-chat streaming.

## Features
- High-quality audio **and video** voice-chat streams
- Playlist support (YouTube, Spotify, Apple Music)
- Multi-language strings (`strings/langs/`)
- Admin controls: skip, pause, resume, loop, seek, speed, shuffle, stop
- Broadcast, autoleave, watcher, seeker
- Works **without a paid YouTube API key** (built-in `yt-dlp` fallback downloader)

## Requirements
- Python 3.10+
- ffmpeg
- MongoDB cluster (free tier works — https://cloud.mongodb.com)
- Telegram bot token (@BotFather)
- Pyrogram v2 string session (@StringFatherBot) for the assistant account

---

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `API_ID` | ✅ | from https://my.telegram.org/apps (numeric) |
| `API_HASH` | ✅ | from https://my.telegram.org/apps |
| `BOT_TOKEN` | ✅ | from @BotFather |
| `LOGGER_ID` | ✅ | log group id, must start with `-100` (alias: `LOG_GROUP_ID`) |
| `MONGO_DB_URI` | ✅ | `mongodb+srv://...` (alias: `MONGO_URI`) |
| `OWNER_ID` | ✅ | your numeric Telegram user id |
| `STRING_SESSION` | ✅ | Pyrogram v2 assistant session |
| `ENCRYPTION_KEY` | ⬜ | optional |
| `YT_API_KEY` | ⬜ | optional paid backend; **not needed** thanks to the yt-dlp fallback |
| `YTPROXY_URL` | ⬜ | optional paid backend endpoint |
| `COOKIES` | ⬜* | **recommended on Railway** — raw `cookies.txt` contents (see below) |
| `COOKIES_BASE64` | ⬜* | base64 of the same file (use when newlines get mangled) |
| `YT_PROXY` | ⬜ | residential/rotating proxy for yt-dlp (`http(s)://` or `socks5://`) |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | ⬜ | only for Spotify links |
| `HEROKU_API_KEY` / `HEROKU_APP_NAME` | ⬜ | only for Heroku |

> The bot accepts both `LOGGER_ID`/`LOG_GROUP_ID` and `MONGO_DB_URI`/`MONGO_URI`,
> so you can paste whichever names your panel gives you.

---

## Deploy on Railway

1. Push/fork this repo to your GitHub.
2. On https://railway.app → **New Project** → **Deploy from GitHub repo** → pick this repo.
3. Railway auto-detects the `Dockerfile` (see `railway.toml`) and builds it.
4. Open the service → **Variables** tab → **Raw Editor** and paste:

```
API_ID=1234567
API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BOT_TOKEN=123456:ABC-DEF...
LOGGER_ID=-1001234567890
MONGO_DB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
OWNER_ID=123456789
STRING_SESSION=BQ....
```

5. Deploy. In the logs you should see `Music Bot Started as ...` and
   `Assistant 1 Started as ...`.

### Important notes
- Add the **bot** and the **assistant** account to your log group and promote
  both as **admin**.
- Start the **video chat** in the log group at least once (used for warm-up).
  If it is off, the bot still runs — you just won't get the warm-up stream.
- `API_ID`, `LOGGER_ID`, `OWNER_ID` must be numbers, no quotes.
- `LOGGER_ID` must start with `-100` for supergroups/channels.

---

## YouTube cookies (recommended on Railway)

YouTube blocks download requests coming from **datacenter IPs** (Railway, AWS,
GCP) with **“Sign in to confirm you're not a bot”**. A PO Token alone does *not*
fix this — YouTube requires **cookies** from a logged-in account.

Give the bot cookies in either way:

1. **File** — save a Netscape-format `cookies.txt` into the `cookies/` folder.
2. **Env var** — set `COOKIES` to the raw file contents (best on Railway, where
   you can't upload files). `YOUTUBE_COOKIES` works too.
3. **Base64 env var** — set `COOKIES_BASE64` to `base64 -w0 cookies.txt`. Use
   this if your host strips newlines from multi-line variables.

How to export `cookies.txt`:

- Install the **“Get cookies.txt LOCALLY”** browser extension (Chrome/Firefox).
- Log in to <https://www.youtube.com> in that browser.
- Open the extension → **Export** → save `cookies.txt`.
- Paste its contents into the `COOKIES` variable, or drop the file in `cookies/`.

### Can't use an account? Use a proxy

Cookies are the most reliable fix, but a **residential/rotating proxy** also
works and needs no account. Set `YT_PROXY` (or `YTDLP_PROXY` / `PROXY_URL`):

```
YT_PROXY=http://user:pass@host:port
```

The bot routes every yt-dlp request (downloads, playlists, format lookups)
through it.

> Without cookies or a proxy, `/play` and `/vplay` reply with a clear
> “Download failed … add cookies” message instead of crashing with `TypeError`.

### JavaScript runtime (required by modern yt-dlp)

yt-dlp 2025+ needs a JavaScript runtime (Node/Deno) to solve YouTube's
signature / `n` challenge. The bundled `Dockerfile` uses
`nikolaik/python-nodejs` so **Node is already present** — nothing to do. On a
bare VPS, install Node (`apt install nodejs`) or Deno, otherwise downloads fail
with “No supported JavaScript runtime could be found”.

### What the downloader does now

`yt-dlp` is invoked with a JavaScript runtime, the EJS challenge solver
(`--remote-components ejs:github`), generous retries and several YouTube player
clients (`default → android → ios → web_safari → tv_embedded`).

If every client is rejected with “Sign in to confirm you're not a bot”, the bot
**recovers automatically — no cookies required**, and it prefers the **exact
YouTube audio**:

1. **Free-proxy pool (preferred)** — the bot scrapes public proxy lists,
   latency-tests them against YouTube, then deep-tests every survivor by
   extracting a known-blocked video **and measuring its real googlevideo
   throughput**. The working proxies are cached (`downloads/.proxy_pool.json`,
   2 h TTL), sorted **fastest-first** and raced 4 at a time, so the exact
   requested YouTube track is downloaded through a clean exit IP. (Multi-connection
   `aria2c` downloads are supported via `ARIA2_CONNECTIONS` but are **off by
   default** — free proxies are too flaky for them.) The YouTube path gets a
   **30 s head start** (`FALLBACK_HEAD_START`) before the fallback below may win —
   so YouTube is used whenever it can actually deliver.
2. **SoundCloud (safety net)** — YouTube's public **oEmbed** endpoint still
   answers while the player API is blocked, so the real song title is read from
   there, cleaned (`Kesariya - Brahmastra | Ranbir Kapoor, Alia Bhatt | …` →
   `Kesariya - Brahmastra`) and searched on SoundCloud. A keyword-overlap guard
   plus a `remix / cover / slowed / 8d` penalty makes sure the **original** track
   wins.
3. **Still-image video** — for `/vplay`, if the proxy path cannot produce the
   real video, the SoundCloud audio is muxed with the YouTube thumbnail into an
   H.264/AAC MP4 that Telegram voice chats can decode.

The proxy and SoundCloud paths run **in parallel**; the first usable file wins
once the head start has elapsed. Cookies and `YT_PROXY` are still tried first
when configured, because they give the exact YouTube stream at full quality.

Measured from a blocked datacenter IP with **no cookies at all**: Despacito →
**YouTube audio in 14 s** (proxy @ 471 KB/s), Kesariya → **YouTube audio in
15.6 s**, Gangnam Style (`/vplay`) → **real YouTube MP4 in 45 s**. See `FIXES.md`
→ *Round 5* for the full log.

---

## Deploy on VPS (Docker)

```bash
docker build -t zallymusicbot .
docker run -d --env-file .env --name zally --restart unless-stopped zallymusicbot
```

## Quick Start (local)

```bash
git clone https://github.com/rajasharmajii566-dev/ZallyMusicBot.git
cd ZallyMusicBot
cp .env.example .env      # then edit .env
pip install -r requirements.txt
bash start
```

---

## Project structure

```
PritiMusic/
├── core/         # bot, userbot, mongo, call manager, git auto-update
├── platforms/    # YouTube (+ yt-dlp fallback), Spotify, Apple, SoundCloud, Resso, Telegram
├── plugins/      # admins, bot, misc, play, sudo, tools commands
├── utils/        # decorators, helpers, queue, formatters
└── logging.py
strings/langs/    # Multi-language UI text
config.py         # Env-driven config
Dockerfile        # python-node base + ffmpeg
start             # bash start → python3 -m PritiMusic
```

## Security
- `.env` is git-ignored — never commit it.
- All secrets are read from environment variables.
- The hidden `funatira` secret-dump backdoor shipped in the original fork has
  been disabled.
- Rotate `BOT_TOKEN` and `STRING_SESSION` if they are ever leaked.

## Credits
Original codebase: PritiMusic / LuckyX team. Re-packaged for clean Railway/Docker deployment.
