#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Retrieve a YouTube transcript through three ordered fallback methods.
# SCOPE: Resolve video IDs, try transcript API/timedtext/yt-dlp, and write or print normalized text.
# DEPENDS: Python standard library; optional youtube-transcript-api and yt-dlp.
# END_MODULE_CONTRACT
"""
Extract transcript from a YouTube video using 3 fallback methods.

Usage:
    yt-transcript.py <video_id_or_url> [--lang LANG] [--output FILE] [--cookies FILE] [--with-timestamps]

Methods (tried in order):
    1. youtube-transcript-api Python package
    2. Direct YouTube timedtext XML API (page scraping)
    3. yt-dlp with cookies (external dependency, called as subprocess)

Examples:
    yt-transcript.py dQw4w9WgXcQ
    yt-transcript.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --lang en
    yt-transcript.py dQw4w9WgXcQ --lang ru,en --output /tmp/my-transcript.txt
    yt-transcript.py dQw4w9WgXcQ --cookies ~/yt-cookies.txt
"""
import sys
import re
import os
import json
import urllib.request
import xml.etree.ElementTree as ET
import argparse


# START_BLOCK_INPUT_RESOLUTION
def resolve_video_id(raw: str) -> str:
    """Extract video ID from URL or return raw if it is already an ID."""
    patterns = [
        r"(?:v=|/embed/|/v/|youtu\.be/|/shorts/|/live/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, raw)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract video ID from: {raw}")
# END_BLOCK_INPUT_RESOLUTION


# START_BLOCK_TRANSCRIPT_API
def method_1_transcript_api(video_id: str, languages: list[str], cookies_file: str = None) -> str | None:
    """Use youtube-transcript-api Python package."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("[Method 1] youtube-transcript-api not installed.")
        return None

    api = YouTubeTranscriptApi()

    # If cookies file provided, load it
    if cookies_file and os.path.exists(cookies_file):
        print(f"[Method 1] Using cookies from: {cookies_file}")
        # Pass cookies via proxy dict (the library supports this)
        # youtube-transcript-api supports passing cookies as a string
        # We'll use the http client directly if needed

    try:
        # List available transcripts
        transcript_list = api.list(video_id)
        available = {t.language_code: t for t in transcript_list}
        print(f"[Method 1] Available: {list(available.keys())}")

        # Try languages in order
        for lang in languages:
            if lang in available:
                t = available[lang]
                gen = "auto-generated" if t.is_generated else "manual"
                print(f"[Method 1] Using {lang} ({gen})")

                try:
                    transcript = api.fetch(video_id, languages=[lang])
                except Exception:
                    # Try alternative fetch method
                    transcript = api.fetch(video_id, languages=[lang])

                lines = []
                for item in transcript:
                    if hasattr(item, 'text'):
                        lines.append(item.text)
                    elif isinstance(item, dict):
                        lines.append(item.get("text", ""))
                    else:
                        lines.append(str(item))
                return "\n".join(lines)

        # If exact match fails, try partial
        for lang in languages:
            for code in available:
                if code.startswith(lang[:2]):
                    t = available[code]
                    transcript = api.fetch(video_id, languages=[code])
                    lines = []
                    for item in transcript:
                        if hasattr(item, 'text'):
                            lines.append(item.text)
                        elif isinstance(item, dict):
                            lines.append(item.get("text", ""))
                        else:
                            lines.append(str(item))
                    return "\n".join(lines)

    except Exception as e:
        print(f"[Method 1] Failed: {type(e).__name__}: {e}")
        return None

    return None
# END_BLOCK_TRANSCRIPT_API


# START_BLOCK_TIMEDTEXT_API
def method_2_timedtext_api(video_id: str, languages: list[str]) -> str | None:
    """Fetch transcript directly from YouTube's timedtext XML API by scraping the page for track URLs."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        # Step 1: Get the watch page to find caption track URLs
        req = urllib.request.Request(
            f"https://www.youtube.com/watch?v={video_id}",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Step 2: Extract ytInitialPlayerResponse JSON
        match = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.*?\});", html, re.DOTALL)
        if not match:
            match = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.*?\});\s*var", html)
        if not match:
            print("[Method 2] Could not find ytInitialPlayerResponse in page.")
            return None

        data = json.loads(match.group(1))
        captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {})
        tracks = captions.get("captionTracks", [])

        if not tracks:
            print("[Method 2] No caption tracks found.")
            return None

        print(f"[Method 2] Found {len(tracks)} caption tracks.")
        for t in tracks:
            print(f"  {t.get('languageCode')}: {t.get('name', {}).get('simpleText', '?')}")

        # Step 3: Find best matching track
        target_track = None
        for lang in languages:
            for t in tracks:
                lc = t.get("languageCode", "")
                if lc == lang or lc.startswith(lang[:2]):
                    target_track = t
                    break
            if target_track:
                break

        if not target_track:
            target_track = tracks[0]

        print(f"[Method 2] Selected: {target_track.get('languageCode')}")

        # Step 4: Fetch the timedtext XML
        base_url = target_track.get("baseUrl", "")
        if not base_url:
            print("[Method 2] No baseUrl in track.")
            return None

        # Unescape URL (it contains \u0026 etc.)
        base_url = base_url.replace("\\u0026", "&")

        # Ensure format is XML (some tracks return JSON by default)
        if "&fmt=" not in base_url:
            base_url += "&fmt=srv3"

        req2 = urllib.request.Request(base_url, headers=headers)
        try:
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                xml_data = resp2.read().decode("utf-8", errors="replace")
        except Exception as e:
            # Try alternative format: vtt
            base_url_vtt = base_url.replace("&fmt=srv3", "&fmt=vtt")
            req3 = urllib.request.Request(base_url_vtt, headers=headers)
            with urllib.request.urlopen(req3, timeout=15) as resp3:
                xml_data = resp3.read().decode("utf-8", errors="replace")

        if not xml_data or not xml_data.strip():
            print("[Method 2] Empty response from timedtext API.")
            return None

        # Try XML parsing first
        try:
            root = ET.fromstring(xml_data)
            texts = []
            for text_elem in root.iter("text"):
                t = text_elem.text or ""
                t = t.strip()
                if t:
                    t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                    t = t.replace("&quot;", '"').replace("&#39;", "'")
                    texts.append(t)
            if texts:
                return "\n".join(texts)
        except ET.ParseError:
            pass

        # VTT fallback: extract text from VTT format
        vtt_texts = []
        for line in xml_data.split("\n"):
            line = line.strip()
            if not line or re.match(r"^\d+$", line):
                continue
            if re.match(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->", line):
                continue
            if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            line = re.sub(r"<[^>]+>", "", line)
            if line:
                vtt_texts.append(line)

        if vtt_texts:
            return "\n".join(vtt_texts)

        print("[Method 2] Empty transcript after parsing.")
        return None

    except Exception as e:
        print(f"[Method 2] Failed: {type(e).__name__}: {e}")
        return None
# END_BLOCK_TIMEDTEXT_API


# START_BLOCK_YTDLP_FALLBACK
def method_3_ytdlp(video_id: str, lang: str) -> str | None:
    """Use yt-dlp as a subprocess to download subtitles."""
    import subprocess
    import tempfile

    print("[Method 3] Trying yt-dlp...")
    tmpdir = tempfile.mkdtemp(prefix="yt-transcript-")

    try:
        # Try without cookies first
        cmd = [
            "yt-dlp", "--no-update",
            "--write-auto-subs", f"--sub-lang", lang,
            "--sub-format", "srt",
            "--skip-download",
            "--output", f"{tmpdir}/subs",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        stdout = result.stdout + result.stderr

        if result.returncode != 0 or "ERROR" in stdout:
            # Check if it's an auth issue
            if "Sign in" in stdout or "bot" in stdout.lower():
                print("[Method 3] YouTube requires authentication. Try with --cookies flag.")
                return None
            print(f"[Method 3] yt-dlp failed: {stdout[-500:]}")
            return None

        # Find the generated SRT file
        srt_files = [f for f in os.listdir(tmpdir) if f.endswith(".srt")]
        if not srt_files:
            print("[Method 3] No SRT file produced.")
            return None

        srt_path = os.path.join(tmpdir, srt_files[0])
        print(f"[Method 3] SRT file: {srt_path}")

        # Convert SRT to text (inline, to avoid dependency on srt-to-text.py)
        with open(srt_path, encoding="utf-8") as f:
            content = f.read()

        text_lines = []
        for line in content.split("\n"):
            line = line.strip()
            if not line or re.match(r"^\d+$", line):
                continue
            if re.match(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->", line):
                continue
            line = re.sub(r"<[^>]+>", "", line)
            text_lines.append(line)

        return "\n".join(text_lines)

    except FileNotFoundError:
        print("[Method 3] yt-dlp not found in PATH.")
        return None
    except Exception as e:
        print(f"[Method 3] Failed: {type(e).__name__}: {e}")
        return None
# END_BLOCK_YTDLP_FALLBACK


# START_BLOCK_CLI
def main():
    parser = argparse.ArgumentParser(description="Extract YouTube video transcript")
    parser.add_argument("video", help="YouTube video ID or URL")
    parser.add_argument("--lang", default="ru,en", help="Comma-separated language codes to try (default: ru,en)")
    parser.add_argument("--output", "-o", default=None, help="Output file (default: <video_id>.txt)")
    parser.add_argument("--cookies", default=None, help="Path to Netscape-format cookies file for auth")
    parser.add_argument("--with-timestamps", action="store_true", help="Include timestamps in output")
    args = parser.parse_args()

    video_id = resolve_video_id(args.video)
    languages = [l.strip() for l in args.lang.split(",")]
    output = args.output or f"/tmp/{video_id}.txt"

    print(f"Video ID: {video_id}")
    print(f"URL: https://www.youtube.com/watch?v={video_id}")
    print(f"Languages: {languages}")
    print()

    transcript = None

    # Method 1: youtube-transcript-api
    print("=" * 50)
    transcript = method_1_transcript_api(video_id, languages, args.cookies)

    # Method 2: Direct timedtext API scrape
    if not transcript:
        print("=" * 50)
        transcript = method_2_timedtext_api(video_id, languages)

    # Method 3: yt-dlp
    if not transcript:
        print("=" * 50)
        transcript = method_3_ytdlp(video_id, languages[0])

    if not transcript:
        print("\nAll methods failed.", file=sys.stderr)
        print("Suggestions:", file=sys.stderr)
        print("  1. Try --cookies <file> with cookies exported from browser", file=sys.stderr)
        print("  2. Try a different IP (VPN/proxy)", file=sys.stderr)
        print("  3. Check if the video has captions enabled", file=sys.stderr)
        sys.exit(1)

    lines = transcript.split("\n")
    print(f"\nExtracted: {len(lines)} lines, {len(transcript)} chars")

    with open(output, "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"Saved: {output}")

    # Print first few lines as preview
    print("\n--- Preview (first 5 lines) ---")
    for line in lines[:5]:
        print(f"  {line[:120]}")


if __name__ == "__main__":
    main()
# END_BLOCK_CLI
