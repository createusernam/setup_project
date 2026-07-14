#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Report required and optional Python dependencies for youtube-transcript.
# SCOPE: Import-check known packages and return nonzero only when a required dependency is missing.
# DEPENDS: Python standard library and the optional packages being inspected.
# END_MODULE_CONTRACT
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
