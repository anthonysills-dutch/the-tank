"""Fetch the wikitext of each "Shark Tank season N" Wikipedia article into data/raw/wikipedia/.

    python scripts/fetch_wikipedia.py

Wikipedia text is CC BY-SA 4.0. We keep only short factual fields from it (who sat on the panel
each episode, a few-word product descriptor, YES/NO), with the revision id recorded for attribution.
Polite: one request at a time, backs off on HTTP 429, skips seasons already fetched.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import DATA_DIR  # noqa: E402

OUT = DATA_DIR / "raw" / "wikipedia"
API = ("https://en.wikipedia.org/w/api.php?action=parse&page=Shark_Tank_season_{s}"
       "&prop=wikitext|revid&format=json&formatversion=2")
UA = "the-tank-research/0.1 (open-source investor-model research)"


def fetch(season, tries=6):
    delay = 30
    for _ in range(tries):
        req = urllib.request.Request(API.format(s=season), headers={"User-Agent": UA})
        try:
            body = urllib.request.urlopen(req, timeout=30).read()
            json.loads(body)
            return body
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            print(f"season {season}: 429, waiting {delay}s", flush=True)
            time.sleep(delay)
            delay *= 2
    raise SystemExit(f"season {season}: still rate limited, try again later")


def main(last=17):
    OUT.mkdir(parents=True, exist_ok=True)
    for s in range(1, last + 1):
        path = OUT / f"season_{s}.json"
        try:
            json.loads(path.read_text(encoding="utf-8"))
            continue
        except (OSError, ValueError):
            pass
        path.write_bytes(fetch(s))
        print(f"season {s}: ok", flush=True)
        time.sleep(5)


if __name__ == "__main__":
    main()
