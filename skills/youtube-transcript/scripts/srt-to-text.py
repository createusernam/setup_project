#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Convert an SRT subtitle file into deduplicated plain text.
# SCOPE: Remove sequence numbers, timestamps, and HTML tags, then write the target text file.
# DEPENDS: Python standard library and a readable SRT input.
# END_MODULE_CONTRACT
"""Convert SRT subtitle file to plain text (strip timestamps and sequence numbers)."""
import sys
import re

if len(sys.argv) < 2:
    sys.exit("usage: srt-to-text.py <input.srt> [output.txt]")

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else (src.rsplit(".", 1)[0] + ".txt")

with open(src, encoding="utf-8") as f:
    content = f.read()

# Remove sequence numbers and timestamps
lines = content.split("\n")
text_lines = []
for line in lines:
    line = line.strip()
    if not line:
        continue
    if re.match(r"^\d+$", line):
        continue
    if re.match(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->", line):
        continue
    # Remove HTML tags from SRT
    line = re.sub(r"<[^>]+>", "", line)
    text_lines.append(line)

# Deduplicate consecutive identical lines (common in auto-generated SRT)
deduped = []
prev = None
for line in text_lines:
    if line != prev:
        deduped.append(line)
    prev = line

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(deduped))

print(f"Saved: {out} ({len(deduped)} lines, {sum(len(l) for l in deduped)} chars)")
