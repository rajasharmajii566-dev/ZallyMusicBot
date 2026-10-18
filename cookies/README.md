# YouTube cookies

YouTube answers requests from datacenter IPs (Railway, AWS, GCP, Heroku, …)
with:

> Sign in to confirm you're not a bot

The only *reliable* fix is to give yt-dlp the cookies of a logged-in YouTube
account. This folder is where the bot looks for them.

## Option 1 — drop a file here

1. Install the **"Get cookies.txt LOCALLY"** browser extension
   (Chrome/Edge/Firefox).
2. Open <https://www.youtube.com> while logged in.
3. Export cookies in **Netscape** format.
4. Save the file as `cookies/cookies.txt`.

## Option 2 — environment variable (best for Railway/Heroku)

Paste the **entire** contents of `cookies.txt` into the `COOKIES` env var, or its
base64 form into `COOKIES_BASE64` (safer when newlines get mangled):

```bash
base64 -w0 cookies.txt        # Linux
base64 -i cookies.txt         # macOS
```

## Option 3 — a residential proxy

If you cannot use an account, set `YT_PROXY` to a residential/rotating proxy:

```
YT_PROXY=http://user:pass@host:port
```

## Notes

* Keep cookies fresh — YouTube expires them. Re-export if downloads start
  failing again.
* Never commit `cookies.txt` to git (it is already git-ignored).
* A PO Token provider helps with bot checks but does **not** bypass IP-based
  login restrictions; cookies are still required on blocked IPs.
