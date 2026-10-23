"""Load and validate Shark profiles (sharks/<slug>/profile.toml).

The rule this enforces: no belief without a verbatim, sourced quote. A profile is either
  status = "sourced"  - every belief quotes a listed source; usable (scripts/check_quotes.py verifies the words)
  status = "stub"     - lens only; never rendered into an agent or a backtest
"""

import tomllib

from . import SHARKS_DIR
from .columns import SHARKS

KINDS = {"own-writing", "interview", "quoted-by-outlet"}
CONFIDENCE = KINDS | {"derived-from-deals"}
WEIGHTS = {"core", "strong", "minor"}
MAX_QUOTE_WORDS = 45


class ProfileError(ValueError):
    pass


def load_raw(slug):
    with open(SHARKS_DIR / slug / "profile.toml", "rb") as fh:
        return tomllib.load(fh)


def load(slug):
    p = load_raw(slug)
    validate(p, slug)
    return p


def validate(p, slug):
    if p.get("slug") != slug or slug not in SHARKS:
        raise ProfileError(f"{slug}: slug mismatch or unknown Shark")
    if p.get("status") not in {"sourced", "stub"}:
        raise ProfileError(f"{slug}: status must be 'sourced' or 'stub'")
    if p["status"] == "stub":
        return
    source_ids = {s["id"] for s in p.get("sources", [])}
    for s in p.get("sources", []):
        if not s.get("url", "").startswith("http"):
            raise ProfileError(f"{slug}: source {s['id']} has no URL")
        if s.get("kind") not in KINDS:
            raise ProfileError(f"{slug}: source {s['id']} has bad kind {s.get('kind')}")
    if not p.get("beliefs"):
        raise ProfileError(f"{slug}: a sourced profile needs beliefs")
    if not p.get("misfires"):
        raise ProfileError(f"{slug}: a sourced profile needs at least one [[misfires]] entry")
    for b in p["beliefs"]:
        if b.get("confidence") not in CONFIDENCE:
            raise ProfileError(f"{slug}/{b.get('id')}: bad confidence {b.get('confidence')}")
        if b.get("weight") not in WEIGHTS:
            raise ProfileError(f"{slug}/{b.get('id')}: bad weight {b.get('weight')}")
        quotes = b.get("quotes", [])
        if not quotes and b["confidence"] != "derived-from-deals":
            raise ProfileError(f"{slug}/{b['id']}: belief has no verbatim quote")
    for owner in p["beliefs"] + p["misfires"]:
        for q in owner.get("quotes", []):
            if q.get("source") not in source_ids:
                raise ProfileError(f"{slug}/{owner.get('id', 'misfire')}: quote cites unknown source {q.get('source')}")
            if len(q["text"].split()) > MAX_QUOTE_WORDS:
                raise ProfileError(f"{slug}/{owner.get('id', 'misfire')}: quote over {MAX_QUOTE_WORDS} words")


def sourced_slugs():
    out = []
    for slug in SHARKS:
        if (SHARKS_DIR / slug / "profile.toml").exists() and load(slug)["status"] == "sourced":
            out.append(slug)
    return out
