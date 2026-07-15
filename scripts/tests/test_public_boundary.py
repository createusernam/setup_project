#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Prevent private methodology vocabulary from leaking into public-bound pipeline skills.
# SCOPE: Scan public skills and canonical public docs while excluding the private methodology package.
# DEPENDS: Python standard library and repository text files.
# END_MODULE_CONTRACT
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "N" + "TO",
    "\u041d\u0422\u041e",
    "\u041f1\u041f",
    "Wu" + "xing",
    "\u0423-\u0421\u0438\u043d",
    "false " + "dichotomy",
    "problem_" + "depth",
    "/method" + "ology",
    "clean " + "prompt",
    "Belief " + "State",
    "quote " + "file",
)
TARGETS = [
    ROOT / "README.md",
    ROOT / "docs" / "human" / "ARCHITECTURE-GUIDE.md",
    ROOT / "docs" / "human" / "PIPELINE.md",
    ROOT / "docs" / "human" / "SETUP.md",
    ROOT / "pipeline-machine.json",
    ROOT / "skills" / "contract" / "SKILL.md",
    ROOT / "skills" / "grace-ontology" / "SKILL.md",
    ROOT / "skills" / "judge" / "SKILL.md",
    ROOT / "skills" / "visualization" / "SKILL.md",
    ROOT / "templates" / "project" / "CLAUDE.md",
    ROOT / "templates" / "project" / "product_brief.md",
]

hits = []
for path in TARGETS:
    text = path.read_text(encoding="utf-8")
    for token in FORBIDDEN:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(token)}(?![A-Za-zА-Яа-я])", text):
            hits.append(f"{path.relative_to(ROOT)}: {token}")
assert not hits, "private vocabulary leak: " + ", ".join(hits)

human_docs = [ROOT / "README.md", ROOT / "AGENTS.md", *(ROOT / "docs" / "human").glob("*.md")]
non_english = []
for path in human_docs:
    if re.search(r"[\u0400-\u04ff]", path.read_text(encoding="utf-8")):
        non_english.append(str(path.relative_to(ROOT)))
assert not non_english, "public human docs must be English: " + ", ".join(non_english)

model_policy_targets = [
    ROOT / "model-routing.json",
    ROOT / "agents" / "team.md",
    ROOT / "docs" / "agent" / "COMPAT.md",
    ROOT / "templates" / "project" / "model-bindings.json",
]
concrete_model_names = ("op" + "us", "son" + "net", "deep" + "seek", "g" + "lm", "gem" + "ini", "g" + "rok")
model_hits = []
for path in model_policy_targets:
    text = path.read_text(encoding="utf-8").lower()
    for name in concrete_model_names:
        if name in text:
            model_hits.append(f"{path.relative_to(ROOT)}: {name}")
assert not model_hits, "concrete model name leaked into public routing policy: " + ", ".join(model_hits)

print("PASS public vocabulary and English human-doc boundary")
