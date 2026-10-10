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
