#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Fetch YouTube subtitle tracks with account cookies and convert them to readable text.
# SCOPE: Download subtitle-only json3 tracks, filter duplicates, and invoke the bundled converter.
# DEPENDS: Bash, yt-dlp, a Netscape cookies file, and json3-to-text.py.
# END_MODULE_CONTRACT
# THE RELIABLE METHOD when YouTube shows "Sign in to confirm you're not a bot"
# or youtube-transcript-api raises RequestBlocked/IpBlocked.
#
# The bot wall is an IDENTITY/IP check: a datacenter/VPN IP (or a rate-limited
# one) is refused UNLESS the request carries a logged-in session. Real browser
# fingerprints and PO tokens do NOT override it — only account cookies do.
#
# Get cookies the ONLY way that survives Chrome/Edge App-Bound Encryption
# (`--cookies-from-browser` fails with "Failed to decrypt with DPAPI" on
# Chrome/Edge >= 127): install the "Get cookies.txt LOCALLY" browser extension,
# open youtube.com (logged in), Export -> a Netscape cookies.txt.
#
# Usage:
#   fetch-with-cookies.sh <cookies.txt> <video-or-playlist-url> [lang_pref] [outdir]
#
# Examples:
#   fetch-with-cookies.sh ~/yt.txt "https://youtu.be/VIDEO"
#   fetch-with-cookies.sh ~/yt.txt "https://youtube.com/playlist?list=PL..." "en-US,en,en.*" ./transcripts
set -euo pipefail

COOK="${1:?cookies.txt required}"
URL="${2:?video or playlist URL required}"
LANG_PREF="${3:-en-US,en,en.*,ru}"
OUTDIR="${4:-./transcripts}"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$OUTDIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --ignore-no-formats-error is REQUIRED: subtitle-only runs otherwise abort with
# "Requested format is not available" when video formats fail (n-sig / no JS runtime).
# --sleep-requests throttles to avoid HTTP 429 on multi-video playlists.
yt-dlp --cookies "$COOK" --no-update --ignore-no-formats-error \
  --sleep-requests 1 \
  --write-subs --write-auto-subs \
  --sub-langs "$LANG_PREF" --sub-format json3 --skip-download \
  -o "$TMP/%(playlist_index|00)s_%(id)s.%(ext)s" "$URL"

shopt -s nullglob
count=0
for f in "$TMP"/*.json3; do
  # skip auto word-level "-orig" tracks (need dedup); prefer clean tracks
  case "$f" in *".en-orig."*|*".orig."*) continue;; esac
  base="$(basename "$f" .json3)"
  python3 "$HERE/json3-to-text.py" "$f" -o "$OUTDIR/$base.txt"
  count=$((count+1))
done
echo "converted $count transcript(s) -> $OUTDIR"
[ "$count" -gt 0 ] || { echo "No subtitles downloaded — check that cookies are logged-in and the video has captions." >&2; exit 1; }
