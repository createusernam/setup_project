#!/usr/bin/env python3
"""Check that required dependencies for youtube-transcript skill are installed."""
import sys
import subprocess

deps = {
    "youtube_transcript_api": "youtube-transcript-api",
    "yt_dlp": "yt-dlp",
}

missing = []
for module, pkg in deps.items():
    try:
        __import__(module)
        print(f"  {pkg} — OK")
    except ImportError:
        print(f"  {pkg} — MISSING")
        missing.append(pkg)

opt_deps = ["browser_cookie3"]
for pkg in opt_deps:
    try:
        __import__(pkg.replace("-", "_"))
        print(f"  {pkg} — OK (optional)")
    except ImportError:
        print(f"  {pkg} — not installed (optional)")

if missing:
    print(f"\nRun: pip install --user {' '.join(missing)}")
    sys.exit(1)
else:
    print("\nAll required dependencies OK.")
    sys.exit(0)
