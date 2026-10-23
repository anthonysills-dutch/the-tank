"""Lint the customer-facing documents against the main ASD-STE100 writing rules that a script can check.

    python scripts/ste_check.py                # checks package_src/**/*.md
    python scripts/ste_check.py path/to/file.md

Checks (STE Issue 9 rule numbers in brackets):
  - procedural sentences (numbered or bulleted steps) over 20 words [R5.1]
  - descriptive sentences over 25 words [R6.1]
  - contractions [R9.x: use full forms]
  - modal verbs that are not approved for instructions: should, could, would, might, may [R3.x; use "must", "can", or a command]
  - common unapproved words with approved alternatives (e.g. "utilize" -> "use", "ensure" -> "make sure")
Tables, code blocks, quotes and headings are skipped. A script cannot check word meanings or
technical-name rules; a human review is still necessary.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODALS = re.compile(r"\b(should|could|would|might|may)\b", re.I)
CONTRACTION = re.compile(r"\b\w+(n't|'re|'ll|'ve|'d|'m)\b|\b(it's|that's|there's|let's|what's)\b", re.I)
UNAPPROVED = {"utilize": "use", "ensure": "make sure", "obtain": "get", "commence": "start", "terminate": "stop",
              "approximately": "about", "prior to": "before", "in order to": "to", "via": "through"}
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")


def check(path):
    problems, in_code = [], False
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line or line.startswith(("#", "|", ">", "<!--", "---")):
            continue
        procedural = bool(re.match(r"^(\d+\.|-|\*)\s", line))
        text = re.sub(r"`[^`]*`|\[([^\]]*)\]\([^)]*\)|\"[^\"]*\"", lambda m: m.group(1) or "X", line)
        text = re.sub(r"^(\d+\.|-|\*)\s+", "", text)
        for s in SENT.split(text):
            words = len(s.split())
            limit = 20 if procedural else 25
            if words > limit:
                problems.append((n, f"{words} words (max {limit}): {s[:90]}"))
        for m in CONTRACTION.finditer(text):
            problems.append((n, f"contraction '{m.group(0)}'"))
        for m in MODALS.finditer(text):
            problems.append((n, f"modal '{m.group(0)}'"))
        for bad, good in UNAPPROVED.items():
            if re.search(rf"\b{bad}\b", text, re.I):
                problems.append((n, f"'{bad}' -> '{good}'"))
    return problems


def main():
    targets = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "package_src").rglob("*.md"))
    total = 0
    for f in targets:
        probs = check(f)
        total += len(probs)
        for n, msg in probs:
            print(f"{f.relative_to(ROOT).as_posix() if f.is_relative_to(ROOT) else f}:{n}: {msg}")
    print(f"{len(targets)} files, {total} STE findings")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
