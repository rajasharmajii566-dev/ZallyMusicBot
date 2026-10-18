"""Multi-source fallback downloader for the music bot.

YouTube answers datacenter IPs (Railway / AWS / GCP / Heroku) with
``Sign in to confirm you're not a bot``.  That is an **IP based** block and no
yt-dlp option can talk its way past it.  Cookies and a residential proxy are
the best fix, but not everybody can supply them, so this module keeps
``/play`` working anyway by chaining several independent strategies:

1. **Proxy pool** - free public HTTP proxies are discovered, validated against
   YouTube and rotated.  A proxy whose exit IP is not flagged downloads the
   video exactly like a normal request would.
2. **SoundCloud** - searched by the *song title*, which we can still read from
   YouTube's public oEmbed endpoint even while the player API is blocked.
3. **Still-image video** - for ``/vplay`` requests, SoundCloud audio is muxed
   with the YouTube thumbnail into an H.264/AAC MP4 so voice chats still get
   something Telegram can decode.

Cookies (``COOKIES`` / ``COOKIES_BASE64`` / ``cookies/cookies.txt``) and
``YT_PROXY`` are always tried first because they give the best quality.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import threading
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

from PritiMusic import LOGGER

logger = LOGGER(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DOWNLOAD_DIR = "downloads"
CACHE_FILE = os.path.join(DOWNLOAD_DIR, ".proxy_pool.json")

# A video that is reliably blocked from datacenter IPs - perfect for probing.
_PROBE_URL = "https://www.youtube.com/watch?v=kJQP7kiw5Fk"

# --------------------------------------------------------------------------
# tunables (env overridable)
# --------------------------------------------------------------------------


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


PROXY_SCAN_LIMIT = _int_env("PROXY_SCAN_LIMIT", 260)
PROXY_POOL_TARGET = _int_env("PROXY_POOL_TARGET", 10)
PROXY_MAX_TRIES = _int_env("PROXY_MAX_TRIES", 5)
PROXY_CACHE_TTL = _int_env("PROXY_CACHE_TTL", 2400)
SOUNDCLOUD_ENABLED = (os.environ.get("SOUNDCLOUD_FALLBACK", "1") or "1").lower() not in (
    "0",
    "false",
    "no",
    "off",
)

_PROXY_LIST_URLS = (
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
)

_PROXY_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}$")

# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

_JS_ALIASES = {
    "node": "node",
    "nodejs": "node",
    "deno": "deno",
    "bun": "bun",
    "qjs": "quickjs",
    "quickjs": "quickjs",
}


def js_runtimes():
    """Return the ``js_runtimes`` mapping yt-dlp needs, or ``None``."""
    for exe in ("node", "nodejs", "deno", "bun", "qjs"):
        if shutil.which(exe):
            return {_JS_ALIASES.get(exe, exe): {}}
    return None


def env_proxy():
    for key in ("YT_PROXY", "YTDLP_PROXY", "PROXY_URL", "HTTPS_PROXY", "HTTP_PROXY"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return None


def base_opts(proxy: str | None = None, extra: dict | None = None) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        "no_color": True,
        "consoletitle": False,
        "logtostderr": False,
        "ignoreerrors": False,
    }
    js = js_runtimes()
    if js:
        opts["js_runtimes"] = js
    opts["remote_components"] = ["ejs:github"]
    if proxy:
        opts["proxy"] = proxy
    if extra:
        opts.update(extra)
    return opts


def _http_json(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


# --------------------------------------------------------------------------
# YouTube oEmbed - gives us title/thumbnail even when the player is blocked
# --------------------------------------------------------------------------


def oembed_meta(vid_id: str):
    """Return ``(title, thumbnail_url)`` for a video id, or ``(None, None)``."""
    url = (
        "https://www.youtube.com/oembed?url="
        f"https://www.youtube.com/watch?v={vid_id}&format=json"
    )
    for endpoint in (url, f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={vid_id}"):
        try:
            data = _http_json(endpoint, timeout=12)
            title = (data.get("title") or "").strip()
            thumb = (data.get("thumbnail_url") or "").strip()
            if title:
                return title, thumb or None
        except Exception:
            continue
    return None, None


_NOISE_WORDS = re.compile(
    r"\b(official|videos?|audio|lyrical|lyrics?|full|songs?|hd|4k|8k|1080p|"
    r"remaster(ed)?|music|visuali[sz]er|mv|m/v|feat\.?|ft\.?|prod\.?|explicit|"
    r"slowed|reverb|remix|cover|version|edit|extended|live|new|latest|"
    r"present(ed|s)?|starring|movie|film|soundtrack|ost|from|the|with)\b",
    re.I,
)


def clean_query(title: str) -> str:
    """Strip noise from a YouTube title so SoundCloud search matches well.

    YouTube titles routinely look like
    ``Kesariya - Brahmastra | Ranbir Kapoor, Alia Bhatt | Pritam | Arijit Singh``
    so we keep only the segment before the first separator - that is the part
    that actually names the song.
    """
    if not title:
        return ""
    q = re.split(r"\s*[|•·»]\s*", title)[0]
    q = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", " ", q)
    q = _NOISE_WORDS.sub(" ", q)
    q = re.sub(r"[_/\\]+", " ", q)
    q = re.sub(r"\s*[-–—]\s*$", "", q)
    q = re.sub(r"\s{2,}", " ", q).strip(" -–—.,")
    if len(q) > 90:
        q = q[:90].rsplit(" ", 1)[0].strip(" -–—.,")
    if not q:
        q = re.split(r"\s*[|•·»]\s*", title)[0].strip()
    return q or title


_STOPWORDS = {
    "the", "and", "for", "with", "from", "song", "video", "audio", "official",
    "full", "new", "hd", "lyrics", "lyrical", "music", "feat", "ft", "prod",
}


def _norm(text: str) -> str:
    """Lower-case and fold accents so ``Brahmāstra`` == ``Brahmastra``."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def _tokens(text: str) -> set:
    return {
        w
        for w in re.findall(r"[a-z0-9\u0900-\u097F]+", _norm(text))
        if len(w) > 2 and w not in _STOPWORDS
    }


# Words that mark a re-upload / derivative rather than the original track.
_VARIANT_WORDS = (
    "remix", "cover", "slowed", "reverb", "mashup", "instrumental", "karaoke",
    "8d", "sped up", "nightcore", "tiktok", "ringtone", "teaser", "trailer",
    "reaction", "tutorial", "loop",
)


def _variant_penalty(title: str) -> int:
    low = _norm(title)
    return sum(1 for w in _VARIANT_WORDS if w in low)


def similarity(query: str, candidate: str) -> float:
    """Fraction of the query's keywords that appear in the candidate title."""
    q, c = _tokens(query), _tokens(candidate)
    if not q or not c:
        return 0.0
    return len(q & c) / len(q)


# --------------------------------------------------------------------------
# proxy pool
# --------------------------------------------------------------------------


class ProxyPool:
    """Discover, validate, cache and rotate free HTTP proxies."""

    def __init__(self) -> None:
        self._good: list[str] = []
        self._bad: set[str] = set()
        self._lock = threading.Lock()
        self._refreshing = False
        self._last_refresh = 0.0
        self._cursor = 0
        self._load()

    # ---------------------------------------------------------------- cache
    def _load(self) -> None:
        try:
            if not os.path.exists(CACHE_FILE):
                return
            with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if time.time() - float(data.get("ts", 0)) > PROXY_CACHE_TTL:
                return
            self._good = [p for p in data.get("good", []) if _PROXY_RE.match(p)]
            self._bad = set(data.get("bad", []))
            self._last_refresh = float(data.get("ts", 0))
            if self._good:
                logger.info(f"Proxy pool: loaded {len(self._good)} cached proxies")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Proxy pool: cache load failed: {exc}")

    def _save(self) -> None:
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            tmp = CACHE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(
                    {"ts": time.time(), "good": self._good, "bad": list(self._bad)[:400]},
                    fh,
                )
            os.replace(tmp, CACHE_FILE)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Proxy pool: cache save failed: {exc}")

    # ------------------------------------------------------------- accessors
    @property
    def size(self) -> int:
        with self._lock:
            return len(self._good)

    def get(self, count: int = PROXY_MAX_TRIES) -> list[str]:
        """Return up to ``count`` live proxies, rotating the start point."""
        with self._lock:
            pool = [p for p in self._good if p not in self._bad]
            if not pool:
                return []
            self._cursor = (self._cursor + 1) % max(len(pool), 1)
            pool = pool[self._cursor :] + pool[: self._cursor]
            return pool[:count]

    def mark_bad(self, proxy: str) -> None:
        with self._lock:
            self._bad.add(proxy)
            if proxy in self._good:
                self._good.remove(proxy)
        self._save()

    def mark_good(self, proxy: str) -> None:
        with self._lock:
            self._bad.discard(proxy)
            if proxy not in self._good:
                self._good.append(proxy)
        self._save()

    # ------------------------------------------------------------- discovery
    @staticmethod
    def _fetch_candidates() -> list[str]:
        found: set[str] = set()

        def grab(url: str):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return resp.read().decode("utf-8", "ignore")
            except Exception:
                return ""

        with ThreadPoolExecutor(max_workers=6) as ex:
            for text in ex.map(grab, _PROXY_LIST_URLS):
                for line in text.splitlines():
                    line = line.strip()
                    if _PROXY_RE.match(line):
                        found.add(line)
        cands = list(found)
        random.shuffle(cands)
        return cands[:PROXY_SCAN_LIMIT]

    @staticmethod
    def _reachable(proxy: str, timeout: int = 8):
        """Return connect latency in seconds, or ``None`` when unusable."""
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler(
                    {"http": f"http://{proxy}", "https": f"http://{proxy}"}
                )
            )
            req = urllib.request.Request(
                "https://www.youtube.com/", headers={"User-Agent": UA}
            )
            start = time.time()
            with opener.open(req, timeout=timeout) as resp:
                if resp.status != 200:
                    return None
                resp.read(1024)
            return time.time() - start
        except Exception:
            return None

    @staticmethod
    def _passes_youtube(proxy: str, timeout: int = 30) -> bool:
        """True when the proxy can actually extract a normally-blocked video."""
        try:
            opts = base_opts(proxy=proxy, extra={"socket_timeout": timeout, "retries": 0,
                                                 "extractor_retries": 0, "simulate": True})
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(_PROBE_URL, download=False)
            return True
        except Exception:
            return False

    def _refresh_sync(self) -> None:
        started = time.time()
        try:
            cands = self._fetch_candidates()
            if not cands:
                logger.warning("Proxy pool: no candidates fetched (list sources unreachable)")
                return
            logger.info(f"Proxy pool: testing {len(cands)} candidate proxies...")

            with ThreadPoolExecutor(max_workers=50) as ex:
                latencies = list(ex.map(self._reachable, cands))
            pairs = [(p, l) for p, l in zip(cands, latencies) if l is not None]
            # fastest first -> downloads through the pool are far quicker
            pairs.sort(key=lambda x: x[1])
            reachable = [p for p, _ in pairs]

            logger.info(f"Proxy pool: {len(reachable)} proxies reach YouTube, deep-testing...")
            if not reachable:
                return

            with ThreadPoolExecutor(max_workers=12) as ex:
                results = list(ex.map(self._passes_youtube, reachable[:80]))

            good = [p for p, ok in zip(reachable[:80], results) if ok]
            with self._lock:
                for p in good:
                    if p not in self._good:
                        self._good.append(p)
                # keep the list bounded
                self._good = self._good[: max(PROXY_POOL_TARGET * 3, 30)]
                self._last_refresh = time.time()
            self._save()
            logger.info(
                f"Proxy pool: {len(good)} working proxies found in "
                f"{time.time() - started:.0f}s (pool size {self.size})"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Proxy pool: refresh failed: {exc}")
        finally:
            with self._lock:
                self._refreshing = False

    async def ensure(self, min_good: int = 1, wait: float = 0.0) -> int:
        """Make sure the pool has at least ``min_good`` proxies."""
        stale = time.time() - self._last_refresh > PROXY_CACHE_TTL
        if self.size >= min_good and not stale:
            return self.size
        with self._lock:
            if self._refreshing:
                already = True
            else:
                already = False
                self._refreshing = True
        if not already:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, self._refresh_sync)
        if wait > 0:
            deadline = time.time() + wait
            while time.time() < deadline:
                if self.size >= min_good:
                    break
                await asyncio.sleep(2)
        return self.size

    async def warmup(self) -> None:
        try:
            n = await self.ensure(min_good=PROXY_POOL_TARGET, wait=0)
            logger.info(f"Proxy pool warmup started (currently {n} proxies)")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Proxy pool warmup failed: {exc}")


PROXY_POOL = ProxyPool()


# --------------------------------------------------------------------------
# SoundCloud fallback
# --------------------------------------------------------------------------


def _sc_search(query: str, limit: int = 10) -> list[dict]:
    opts = base_opts(
        extra={
            "extract_flat": True,
            "skip_download": True,
            "noplaylist": False,
            "playlistend": limit,
        }
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"scsearch{limit}:{query}", download=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"SoundCloud search failed for {query!r}: {exc}")
        return []

    tracks = []
    for entry in (info or {}).get("entries") or []:
        if not entry:
            continue
        url = entry.get("url") or entry.get("webpage_url")
        if not url and entry.get("id"):
            url = f"https://soundcloud.com/{entry['id']}"
        if not url:
            continue
        tracks.append(
            {
                "url": url,
                "title": entry.get("title") or "",
                "duration": entry.get("duration") or 0,
            }
        )
    return tracks


def _sc_download(track_url: str, out_base: str) -> str | None:
    opts = base_opts(
        extra={
            "outtmpl": out_base + ".%(ext)s",
            "format": "bestaudio/best",
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([track_url])
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"SoundCloud download failed ({track_url}): {str(exc)[:140]}")
        return None
    target = out_base + ".mp3"
    if os.path.exists(target) and os.path.getsize(target) > 0:
        return target
    for cand in (out_base + ".m4a", out_base + ".opus", out_base + ".webm"):
        if os.path.exists(cand) and os.path.getsize(cand) > 0:
            return cand
    return None


SOUNDCLOUD_MIN_MATCH = float(os.environ.get("SOUNDCLOUD_MIN_MATCH", "") or 0.5)


def soundcloud_audio(query: str, out_base: str) -> str | None:
    """Search SoundCloud for ``query`` and download the best matching track.

    Only tracks whose title shares enough keywords with the query are accepted,
    so we never silently play the wrong song.
    """
    tracks = _sc_search(query, limit=12)
    if not tracks:
        return None

    for track in tracks:
        track["_sim"] = similarity(query, track.get("title") or "")

    ranked = [t for t in tracks if t["_sim"] >= SOUNDCLOUD_MIN_MATCH]
    if not ranked:
        best = max((t["_sim"] for t in tracks), default=0.0)
        logger.info(
            f"SoundCloud: no close match for {query!r} (best similarity {best:.2f})"
        )
        return None

    def rank(t: dict):
        d = t.get("duration") or 0
        sane = 0 if 25 <= d <= 1200 else (1 if d > 1200 else 2)
        return (-t["_sim"], _variant_penalty(t.get("title") or ""), sane)

    ranked.sort(key=rank)
    for track in ranked[:4]:
        logger.info(f"SoundCloud trying ({track['_sim']:.2f}): {track['title'][:70]}")
        path = _sc_download(track["url"], out_base)
        if path:
            return path
    return None


# --------------------------------------------------------------------------
# still-image video (thumbnail + audio -> mp4)
# --------------------------------------------------------------------------


def _download_thumb(vid_id: str, thumb_url: str | None, dest: str) -> bool:
    urls = []
    if thumb_url:
        urls.append(thumb_url)
    urls += [
        f"https://i.ytimg.com/vi/{vid_id}/maxresdefault.jpg",
        f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            if len(data) > 2000:
                with open(dest, "wb") as fh:
                    fh.write(data)
                return True
        except Exception:
            continue
    return False


def make_still_video(vid_id: str, audio_path: str, out_path: str,
                     thumb_url: str | None = None) -> str | None:
    """Mux a still image with audio into a Telegram-friendly H.264/AAC mp4."""
    img = os.path.join(DOWNLOAD_DIR, f"{vid_id}.thumb.jpg")
    if not os.path.exists(img) and not _download_thumb(vid_id, thumb_url, img):
        # last resort: a plain grey frame
        img = os.path.join(DOWNLOAD_DIR, f"{vid_id}.thumb.jpg")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                 "color=c=0x1b1b1b:s=1280x720", "-frames:v", "1", img],
                check=True, timeout=60,
            )
        except Exception:
            return None
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", img,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-r", "10",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest", out_path,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=900)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"still-video mux failed for {vid_id}: {str(exc)[:140]}")
        return None
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    return None


# --------------------------------------------------------------------------
# orchestrator
# --------------------------------------------------------------------------


def _ytdlp_with_proxy(vid_id: str, video: bool, proxy: str) -> str | None:
    url = f"https://www.youtube.com/watch?v={vid_id}"
    out_base = os.path.join(DOWNLOAD_DIR, vid_id)
    if video:
        target = out_base + ".mp4"
        fmt = (
            "bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            "bestvideo[height<=720][vcodec!*=av01]+bestaudio/"
            "best[height<=720][vcodec^=avc1]/best[height<=720]/best"
        )
    else:
        target = out_base + ".mp3"
        fmt = "bestaudio/best"

    if os.path.exists(target) and os.path.getsize(target) > 0:
        return target

    opts = base_opts(proxy=proxy, extra={"outtmpl": out_base + ".%(ext)s", "format": fmt})
    if video:
        opts["merge_output_format"] = "mp4"
    else:
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
             "preferredquality": "192"}
        ]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"proxy download failed via {proxy}: {str(exc)[:120]}")
        return None

    if os.path.exists(target) and os.path.getsize(target) > 0:
        return target
    import glob as _glob

    for f in _glob.glob(out_base + ".*"):
        if f.endswith((".mp3", ".mp4", ".m4a", ".webm", ".mkv")) and os.path.getsize(f) > 0:
            return f
    return None


async def _try_proxies(vid_id: str, video: bool) -> str | None:
    if (os.environ.get("PROXY_POOL_ENABLED", "1") or "1").lower() in ("0", "false", "no", "off"):
        return None
    # Give a cold pool a short chance to fill up.
    await PROXY_POOL.ensure(min_good=1, wait=25 if PROXY_POOL.size == 0 else 0)
    proxies = PROXY_POOL.get(PROXY_MAX_TRIES)
    if not proxies:
        return None
    loop = asyncio.get_running_loop()
    logger.info(f"YouTube blocked -> trying {len(proxies)} pooled proxies for {vid_id}")
    for proxy in proxies:
        try:
            path = await asyncio.wait_for(
                loop.run_in_executor(None, _ytdlp_with_proxy, vid_id, video, proxy),
                timeout=600,
            )
        except Exception:
            path = None
        if path:
            PROXY_POOL.mark_good(proxy)
            logger.info(f"Downloaded {vid_id} through proxy {proxy}")
            return path
        PROXY_POOL.mark_bad(proxy)
    return None


async def _try_soundcloud(vid_id: str, video: bool, title: str | None) -> str | None:
    """Search SoundCloud by the song title and download the best match."""
    if not SOUNDCLOUD_ENABLED:
        return None
    loop = asyncio.get_running_loop()
    thumb_url = None
    if not title:
        try:
            title, thumb_url = await asyncio.wait_for(
                loop.run_in_executor(None, oembed_meta, vid_id), timeout=25
            )
        except Exception:
            title = None

    query = clean_query(title or vid_id)
    out_base = os.path.join(DOWNLOAD_DIR, vid_id)
    logger.info(f"SoundCloud fallback for {vid_id} (query={query!r})")

    try:
        audio = await asyncio.wait_for(
            loop.run_in_executor(None, soundcloud_audio, query, out_base), timeout=420
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"SoundCloud fallback error for {vid_id}: {exc}")
        return None

    if not audio:
        return None
    if not video:
        return audio

    # /vplay -> mux the SoundCloud audio with the YouTube thumbnail
    try:
        out = await asyncio.wait_for(
            loop.run_in_executor(
                None, make_still_video, vid_id, audio, out_base + ".mp4", thumb_url
            ),
            timeout=900,
        )
        if out:
            return out
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"still-video fallback error for {vid_id}: {exc}")
    # Better an audio-only track than nothing at all.
    return audio


async def fallback_download(vid_id: str, video: bool = False,
                            title: str | None = None) -> str | None:
    """Last-resort download that does not depend on this server's IP.

    The proxy pool (exact YouTube audio) and SoundCloud (fast, title matched)
    run **in parallel**.  The proxy gets a short head start so that when it is
    quick we still deliver the exact requested track; otherwise whichever
    source produces a usable file first wins.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    proxy_task = asyncio.create_task(_try_proxies(vid_id, video))
    sc_task = asyncio.create_task(_try_soundcloud(vid_id, video, title))

    head_start = _int_env("FALLBACK_HEAD_START", 0)
    try:
        done, _ = await asyncio.wait({proxy_task}, timeout=head_start)
        if proxy_task in done:
            res = None
            try:
                res = proxy_task.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"proxy fallback error for {vid_id}: {exc}")
            if res:
                sc_task.cancel()
                return res
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"proxy fallback error for {vid_id}: {exc}")

    pending = {t for t in (proxy_task, sc_task) if not t.done()}
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                res = task.result()
            except Exception:  # noqa: BLE001
                res = None
            if res:
                for other in pending:
                    other.cancel()
                return res
    return None
