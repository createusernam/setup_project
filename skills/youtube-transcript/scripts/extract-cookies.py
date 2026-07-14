#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Export YouTube browser cookies into a Netscape-compatible file for authenticated retrieval.
# SCOPE: Select a supported local browser, filter youtube.com cookies, and write the requested output.
# DEPENDS: Python standard library and browser-cookie3.
# END_MODULE_CONTRACT
"""
Extract YouTube cookies from a browser for yt-dlp / youtube-transcript-api auth.

Usage:
    extract-cookies.py --browser chrome --output /tmp/yt-cookies.txt
    extract-cookies.py --browser firefox --output /tmp/yt-cookies.txt
    extract-cookies.py --browser chromium --output /tmp/yt-cookies.txt

Requires: pip install --user browser-cookie3
"""
import sys
import os

try:
    import browser_cookie3
except ImportError:
    print("Error: browser-cookie3 not installed.", file=sys.stderr)
    print("Run: pip install --user browser-cookie3", file=sys.stderr)
    sys.exit(1)


def extract_cookies(browser: str) -> list:
    """Extract YouTube cookies from browser."""
    browsers = {
        "chrome": browser_cookie3.chrome,
        "chromium": browser_cookie3.chromium,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "brave": browser_cookie3.brave,
        "opera": browser_cookie3.opera,
    }

    if browser not in browsers:
        print(f"Unknown browser: {browser}", file=sys.stderr)
        print(f"Available: {list(browsers.keys())}", file=sys.stderr)
        sys.exit(1)

    try:
        cj = browsers[browser](domain_name="youtube.com")
        cookies = []
        for cookie in cj:
            if "youtube" in cookie.domain:
                cookies.append(cookie)
        return cookies
    except Exception as e:
        print(f"Error reading {browser} cookies: {e}", file=sys.stderr)
        print("Make sure browser is closed before extracting cookies.", file=sys.stderr)
        sys.exit(1)


def write_netscape(cookies: list, path: str):
    """Write cookies in Netscape format (compatible with yt-dlp and youtube-transcript-api)."""
    with open(path, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Extracted by youtube-transcript skill\n")
        f.write("# https://curl.se/docs/http-cookies.html\n\n")
        for c in cookies:
            domain = c.domain if c.domain.startswith(".") else f".{c.domain}"
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            secure = "TRUE" if c.secure else "FALSE"
            expiry = str(int(c.expires)) if c.expires else "0"
            f.write(f"{domain}\t{flag}\t{c.path}\t{secure}\t{expiry}\t{c.name}\t{c.value}\n")


def main():
    if len(sys.argv) != 5 or sys.argv[1] != "--browser" or sys.argv[3] != "--output":
        print("Usage: extract-cookies.py --browser <browser> --output <file>", file=sys.stderr)
        print("Browsers: chrome, chromium, firefox, edge, brave, opera", file=sys.stderr)
        sys.exit(1)

    browser = sys.argv[2]
    output = sys.argv[4]

    print(f"Extracting YouTube cookies from {browser}...")
    cookies = extract_cookies(browser)

    if not cookies:
        print("No YouTube cookies found. Are you logged into YouTube in this browser?")
        sys.exit(1)

    write_netscape(cookies, output)
    print(f"Exported {len(cookies)} cookies to {output}")


if __name__ == "__main__":
    main()
