#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Convert YouTube json3 subtitle events into deduplicated readable text.
# SCOPE: Extract caption fragments, optionally preserve lines, and write or print reflowed prose.
# DEPENDS: Python standard library and a yt-dlp json3 subtitle file.
# END_MODULE_CONTRACT
"""
Convert a yt-dlp `json3` subtitle file into clean, readable prose.

json3 is YouTube's timedtext JSON. Manual tracks give one caption fragment per
event; joining fragments with spaces and re-wrapping yields clean prose without
the rolling-duplicate artifacts you get from auto-caption VTT.

Usage:
    json3-to-text.py <input.json3> [-o output.txt] [--width 100] [--keep-lines]

    --keep-lines : keep original caption-fragment line breaks instead of
                   reflowing into wrapped prose (useful for alignment/timing work)
"""
import argparse, json, re, sys, textwrap


def json3_to_fragments(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    frags = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        t = "".join(s.get("utf8", "") for s in segs)
        if t.strip():
            frags.append(t)
    return frags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--width", type=int, default=100)
    ap.add_argument("--keep-lines", action="store_true")
    args = ap.parse_args()

    frags = json3_to_fragments(args.input)
    if not frags:
        print("No caption fragments found (empty or non-json3 file).", file=sys.stderr)
        sys.exit(1)

    if args.keep_lines:
        out = "\n".join(f.replace("\n", " ").strip() for f in frags)
    else:
        text = re.sub(r"\s+", " ", " ".join(frags)).strip()
        out = "\n".join(
            textwrap.wrap(text, width=args.width,
                          break_long_words=False, break_on_hyphens=False)
        )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        words = len(re.sub(r"\s+", " ", " ".join(frags)).split())
        print(f"wrote {args.output}  ({words} words, {len(out)} chars)")
    else:
        print(out)


if __name__ == "__main__":
    main()
