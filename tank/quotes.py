"""Verify that every quote in a Shark profile is word for word in the source it cites.

The corpus (sharks/<slug>/corpus/<id>.txt) is fetched by scripts/fetch_sources.py and gitignored.
Normalization ignores case, curly quotes, punctuation and whitespace; words are not ignored. A quote may skip words with "..." and each piece is checked.
"""

import re

from . import SHARKS_DIR


def norm(s):
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"'\s+(t|s|re|ll|ve|d|m)\b", r"'\1", s)
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def corpus_text(slug, source_id):
    path = SHARKS_DIR / slug / "corpus" / f"{source_id}.txt"
    return norm(path.read_text(encoding="utf-8")) if path.exists() else None


def found(quote, haystack):
    pieces = [norm(p) for p in re.split(r"\.\.\.|…", quote)]
    pieces = [p for p in pieces if len(p.split()) >= 3]
    return bool(pieces) and all(p in haystack for p in pieces)


def check_profile(profile):
    """-> (verified, problems). A problem is (belief_id, source_id, quote, reason)."""
    slug = profile["slug"]
    cache, verified, problems = {}, 0, []
    entries = [(b["id"], b) for b in profile.get("beliefs", [])]
    entries += [(f"misfire-{i + 1}", m) for i, m in enumerate(profile.get("misfires", []))]
    for owner, b in entries:
        for q in b.get("quotes", []):
            sid = q["source"]
            if sid not in cache:
                cache[sid] = corpus_text(slug, sid)
            hay = cache[sid]
            if hay is None:
                problems.append((owner, sid, q["text"], "source not in corpus (run scripts/fetch_sources.py)"))
            elif not found(q["text"], hay):
                problems.append((owner, sid, q["text"], "not found verbatim in source"))
            else:
                verified += 1
    return verified, problems
