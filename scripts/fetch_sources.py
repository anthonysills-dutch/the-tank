"""Fetch every source a Shark profile cites into a local corpus, one plain-text file per source.

    python scripts/fetch_sources.py cuban                 # fetch any source not yet in the corpus
    python scripts/fetch_sources.py cuban --refetch S03   # fetch one again

Writes sharks/<slug>/corpus/<id>.txt and sharks/<slug>/corpus/sources.json (id, url, words, fetched).
The corpus is gitignored: it is copyrighted text kept only so quotes can be checked word for word.
Only the short quotes in profile.toml ship.
"""

import argparse
import datetime
import html
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import SHARKS_DIR  # noqa: E402
from tank.profiles import load_raw  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside", "button", "figure"}
COMMENTS = re.compile(r"^(\d+ (thoughts|responses|comments) on\b|Leave a (Reply|comment)\b|Comment by\b|Pingback:)", re.I)
BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "blockquote", "section", "article", "tr"}


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif tag in BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self.skip:
            self.skip -= 1
        elif tag in BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def to_text(raw):
    p = Text()
    p.feed(raw)
    text = html.unescape("".join(p.out))
    lines = [re.sub(r"[ \t ]+", " ", l).strip() for l in text.splitlines()]
    # Stop at the comment section: a reader's words must never verify as the Shark's.
    for i, l in enumerate(lines):
        if COMMENTS.match(l):
            lines = lines[:i]
            break
    return "\n".join(l for l in lines if l)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--refetch", nargs="*", default=[])
    args = ap.parse_args()

    profile = load_raw(args.slug)
    corpus = SHARKS_DIR / args.slug / "corpus"
    corpus.mkdir(exist_ok=True)
    table_path = corpus / "sources.json"
    table = json.loads(table_path.read_text(encoding="utf-8")) if table_path.exists() else {}

    for s in profile.get("sources", []):
        path = corpus / f"{s['id']}.txt"
        if path.exists() and s["id"] not in args.refetch:
            continue
        try:
            text = to_text(fetch(s["url"]))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            print(f"fail  {s['id']}: {e}")
            table[s["id"]] = {"url": s["url"], "status": f"fail: {e}"}
            continue
        words = len(text.split())
        status = "thin" if words < 300 else "ok"
        path.write_text(f"Source: {s['id']} | {s['url']}\n\n{text}\n", encoding="utf-8")
        table[s["id"]] = {"url": s["url"], "status": status, "words": words,
                          "fetched": datetime.date.today().isoformat()}
        print(f"{status:5s} {s['id']}: {words} words")

    table_path.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
