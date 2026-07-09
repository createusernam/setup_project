---
name: youtube-transcript
description: "Extract transcripts (subtitles) from YouTube videos. Use when user needs to get text of what was said in a YouTube video, download subtitles, get captions, read video content, extract speech from video, get transcript from YouTube, or says 'transcript', 'subtitles', 'captions', 'what did they say in this video', 'extract text from video', 'субтитры', 'транскрипт', 'расшифровка видео'. Supports auto-generated and manual captions in any language."
---

# Youtube Transcript

IRON LAW: NEVER give up after one method fails. Try the methods in order until one succeeds.

## Read this first — the 2025+ reality

YouTube now aggressively gates the player/transcript endpoints. If you see
**"Sign in to confirm you're not a bot"** (yt-dlp) or **`RequestBlocked`/`IpBlocked`**
(youtube-transcript-api), the request was refused on **identity/IP grounds**, not
format. On a datacenter IP, a VPN exit, or a rate-limited residential IP, the
anonymous methods (1–3) will ALL fail — including a real browser and a valid PO
token. Proven: a genuine Playwright browser gets a caption-stripped player
response, and a correctly-minted bgutil PO token is still refused. **The only
thing that reliably passes the wall is a logged-in session → go to Method C.**

```
Progress:
- [ ] Step 1: Check dependencies
- [ ] Step 2: Method 1 — youtube-transcript-api  (fast; works on clean IPs)
- [ ] Step 3: Method 2 — yt-dlp player clients    (if M1 blocked)
- [ ] Step 4: Method 3 — direct timedtext scrape  (if M1–2 blocked)
- [ ] Step 5: Method C — yt-dlp + cookies.txt      ← RELIABLE when "not a bot" wall appears
- [ ] Step 6: Save clean text and report which method worked
```

## Step 1: Check dependencies

```bash
python3 scripts/check-deps.py     # installs: pip install --user youtube-transcript-api yt-dlp
```

## Method 1 — youtube-transcript-api (try first)

```bash
python3 scripts/yt-transcript.py <video_id_or_url> --lang en,ru --output out.txt
```
Fast when the IP is clean. On `RequestBlocked` → the IP is flagged; skip to Method C.

## Method 2 — yt-dlp player clients (if M1 blocked)

```bash
yt-dlp --write-auto-subs --sub-lang en --sub-format vtt --skip-download -o out "<url>"
# try alternate clients: --extractor-args "youtube:player_client=tv,ios,mweb,web_safari"
```
If every client says "Sign in to confirm you're not a bot" → go to Method C.

## Method 3 — direct timedtext scrape (rarely helps when IP-flagged)

`scripts/yt-transcript.py` tries this automatically. Note: on a flagged IP the
watch page's `ytInitialPlayerResponse` comes back with **no caption tracks**, so
this fails too. Kept only for the rare "captions hidden from API but page works" case.

## Method C — yt-dlp + exported cookies.txt  ⭐ THE RELIABLE ONE

A logged-in session bypasses the bot wall even from a flagged/VPN/datacenter IP.

### 1. Get cookies the RIGHT way

Do **NOT** use `yt-dlp --cookies-from-browser`: on Chrome/Edge ≥ 127 it fails with
`Failed to decrypt with DPAPI` (App-Bound Encryption, v20 cookies) — the key is
unreachable from outside the running browser, and the DB is exclusively locked
while the browser is open.

The one method that survives ABE: read cookies **from inside** the browser via the
**"Get cookies.txt LOCALLY"** extension.
1. Log in to `youtube.com` in the browser.
2. Install the extension (Chrome Web Store / Edge Add-ons).
3. On the youtube.com tab: extension → **Export** → downloads a Netscape `cookies.txt`.

Sanity-check it carries a session (must contain these):
```bash
grep -oiE "(SID|__Secure-1PSID|LOGIN_INFO|SAPISID)" cookies.txt | sort -u
```

### 2. Fetch + convert (single video OR whole playlist)

```bash
scripts/fetch-with-cookies.sh cookies.txt "<video-or-playlist-url>" "en-US,en,en.*" ./transcripts
```

The exact flags that matter (the wrapper uses them):
```bash
yt-dlp --cookies cookies.txt --ignore-no-formats-error \
  --sleep-requests 1 \
  --write-subs --write-auto-subs --sub-langs "en-US,en,en.*" \
  --sub-format json3 --skip-download -o "%(playlist_index)s_%(id)s.%(ext)s" "<url>"
```
- `--ignore-no-formats-error` is **mandatory**: subtitle-only runs otherwise abort with
  "Requested format is not available" when video formats fail (n-sig / no JS runtime).
- `--sub-format json3` → cleanest source; convert with `scripts/json3-to-text.py`
  (joins fragments into prose; no VTT rolling-duplicate mess).
- **Prefer the manual track** (`en-US` / `en`) over auto (`en-en-US`, `en-orig`).
  `*-orig` is auto word-level (huge, needs dedup) — the wrapper skips it.

### 3. Convert a json3 file on its own
```bash
python3 scripts/json3-to-text.py video.en-US.json3 -o transcript.txt          # wrapped prose
python3 scripts/json3-to-text.py video.en-US.json3 --keep-lines               # keep caption lines
```

## Environment gotchas (WSL2 + Windows VPN)

- **WSL2 rides the Windows default route.** If Windows runs a full-tunnel VPN
  (WireGuard / tun2socks), WSL egresses through the SAME exit IP. Check:
  `curl -s https://api.ipify.org` (WSL) vs `powershell.exe -c "(irm https://api.ipify.org)"` — if
  equal and it's a hosting/OVH-type IP (`curl ip-api.com/json/<ip>`), that datacenter IP is
  why YouTube walls you. The VPN is the cause, not the cure — use Method C cookies.
- Windows-side `yt-dlp.exe` runs through the VPN too (same wall) and its
  `--cookies-from-browser` hits the SAME ABE/lock problems. No advantage.
- After many requests you may get **HTTP 429**. Back off: wait, keep `--sleep-requests 1`,
  don't parallelize. A downgraded `tv player API JSON` with "no subtitles" is a throttle
  symptom — retry later, don't assume the video lacks captions.

## Anti-Patterns

- Don't retry anonymous methods forever once you see "not a bot" — that's an IP/identity
  wall; only cookies (Method C) fix it.
- Don't use `--cookies-from-browser` on modern Chrome/Edge — App-Bound Encryption breaks it.
  Use the cookies.txt extension export.
- Don't forget `--ignore-no-formats-error` for subtitle-only pulls.
- Don't parse VTT auto-captions naively (rolling duplicates) — use `json3` + `json3-to-text.py`.
- Don't use `youtube-dl` (deprecated) — use `yt-dlp`.
- Don't hammer YouTube in parallel — you'll earn a 429 and poison the session/IP.

## Pre-Delivery Checklist

- [ ] Output saved to filesystem (not just printed), non-empty
- [ ] Correct track chosen (manual > auto; right language)
- [ ] User knows which method worked (record it for next time)
