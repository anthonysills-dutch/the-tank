"""Check quotes: in a Shark profile against its sources, or in a Shark's verdict against its profile.

    python scripts/check_quotes.py cuban                          # profile quotes vs the fetched corpus
    python scripts/check_quotes.py --all
    python scripts/check_quotes.py cuban --verdict verdict.json   # quotes a Shark agent wrote vs its profile

Profile mode needs the local corpus (python scripts/fetch_sources.py <slug>). Verdict mode needs only
the profile: anything a Shark agent puts in quotation marks must be one of its verified quotes.
Exit code 1 if any quote fails.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank.profiles import load, sourced_slugs  # noqa: E402
from tank.quotes import check_profile, found, norm  # noqa: E402

QUOTED = re.compile(r"[\"“]([^\"“”]{12,400})[\"”]")


def check_verdict(slug, path):
    profile = load(slug)
    bank = " | ".join(norm(q["text"]) for b in profile["beliefs"] + profile.get("misfires", []) for q in b.get("quotes", []))
    text = Path(path).read_text(encoding="utf-8")
    try:
        text = " ".join(str(v) for v in _strings(json.loads(text)))
    except json.JSONDecodeError:
        pass
    quotes = [q for q in QUOTED.findall(text) if len(norm(q).split()) >= 4]
    bad = [q for q in quotes if not found(q, bank)]
    print(f"{slug} verdict: {len(quotes) - len(bad)} quotes match the profile, {len(bad)} do not")
    for q in bad:
        print(f"  NOT IN PROFILE: \"{q[:120]}\"")
    return not bad


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--verdict", help="A Shark agent's verdict (JSON or text) to check against the profile")
    args = ap.parse_args()

    if args.verdict:
        sys.exit(0 if check_verdict(args.slug, args.verdict) else 1)

    failed = False
    for slug in (sourced_slugs() if args.all else [args.slug]):
        verified, problems = check_profile(load(slug))
        print(f"{slug}: {verified} quotes verified verbatim, {len(problems)} problems")
        for owner, sid, text, reason in problems:
            print(f"  {owner} [{sid}] {reason}: \"{text[:110]}\"")
        failed |= bool(problems)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
