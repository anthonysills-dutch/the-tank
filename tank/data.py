"""Load the raw CSV, turn each row into a pitch record, and anonymize what the model sees.

Every pitch record has three parts:
  card    - the only thing a model ever sees: anonymized, no names, no dates, no season
  secret  - identifying details, used only to score the memorization probe
  outcome - what actually happened, used only for scoring and for precedents
"""

import csv
import json
import re
from datetime import datetime

from .columns import SHARKS, resolve

PLACEHOLDER_CO = "[COMPANY]"
PLACEHOLDER_FOUNDER = "[FOUNDER]"
STOP = {"the", "and", "inc", "llc", "co", "company", "for", "of", "by", "a", "an"}
DATE_FORMATS = ("%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y")


def num(value):
    """Parse '$1,200,000', '10%', '', 'NaN' -> float or None."""
    if value is None:
        return None
    s = str(value).strip().replace("$", "").replace(",", "").replace("%", "")
    if s == "" or s.lower() in {"nan", "na", "n/a", "none", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def flag(value):
    v = num(value)
    if v is not None:
        return v > 0
    s = str(value or "").strip().lower()
    if s in {"yes", "y", "true"}:
        return True
    if s in {"no", "n", "false"}:
        return False
    return None


def iso_date(value):
    s = str(value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _name_tokens(text):
    # Names in this dataset are often CamelCase-joined ("PuppyCake") while descriptions spell them out.
    words = re.findall(r"[A-Za-z][A-Za-z'\-]+", text or "")
    parts = [p for w in words for p in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z']+", w)]
    return [t for t in dict.fromkeys(words + parts) if len(t) >= 3 and t.lower() not in STOP]


MOJIBAKE = re.compile(r"[‚ÂÃâ][\u0080-ÿ‘-„†-™]{1,3}")


def fix_text(s):
    """Repair UTF-8 text that was mis-decoded as Mac Roman or Latin-1 somewhere upstream ("Brewer‚Äôs")."""
    def repair(m):
        for enc in ("mac_roman", "cp1252", "latin-1"):
            try:
                return m.group(0).encode(enc).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        return m.group(0)
    return MOJIBAKE.sub(repair, s or "").replace("’", "'").replace("‘", "'")


def anonymize(description, name, entrepreneurs, website):
    """Strip the company name, founder names and web addresses from a description."""
    text = fix_text(description)
    name, entrepreneurs = fix_text(name), fix_text(entrepreneurs)
    text = re.sub(r"https?://\S+|www\.\S+|\b[\w-]+\.(com|net|org|co|io)\b", "[WEBSITE]", text, flags=re.I)
    if website:
        domain = re.sub(r"^https?://(www\.)?", "", website.strip(), flags=re.I).split("/")[0]
        if domain:
            text = re.sub(re.escape(domain), "[WEBSITE]", text, flags=re.I)
    if name:
        text = re.sub(re.escape(name.strip()), PLACEHOLDER_CO, text, flags=re.I)
    for source, ph in ((name, PLACEHOLDER_CO), (entrepreneurs, PLACEHOLDER_FOUNDER)):
        for tok in _name_tokens(source):
            # Match regardless of straight/curly/missing apostrophes ("Brewer's" vs "Brewer’s" vs "Brewers").
            letters = [c for c in tok if c.isalnum()]
            pattern = r"['’’]?".join(re.escape(c) for c in letters)
            text = re.sub(rf"\b{pattern}\b", ph, text, flags=re.I)
    for ph in (PLACEHOLDER_CO, PLACEHOLDER_FOUNDER):
        text = re.sub(rf"(?:{re.escape(ph)}\s*)+", ph + " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def build_records(rows, cols):
    records = []
    for i, row in enumerate(rows):
        g = lambda f: row.get(cols[f]) if f in cols else None  # noqa: E731
        season, episode = num(g("season")), num(g("episode"))
        if season is None:
            continue
        pitch_no = num(g("pitch")) or (i + 1)
        ask, equity = num(g("ask_amount")), num(g("ask_equity"))
        valuation = num(g("valuation"))
        if valuation is None and ask and equity:
            valuation = round(ask / (equity / 100.0))
        multiple = flag(g("multiple_founders"))

        card = {
            "industry": (g("industry") or "").strip() or None,
            "description": anonymize(g("description"), g("name"), g("entrepreneurs"), g("website")),
            "ask_amount": ask,
            "ask_equity_pct": equity,
            "implied_valuation": valuation,
            "team": None if multiple is None else ("multiple founders" if multiple else "solo founder"),
        }
        for f in ("yearly_revenue", "monthly_revenue", "gross_margin", "net_margin"):
            if f in cols:
                card[f] = num(g(f))
        for f in ("has_patents", "bootstrapped"):
            if f in cols:
                card[f] = flag(g(f))

        per_shark = {}
        for slug in SHARKS:
            amount, eq = num(g(f"{slug}_amount")), num(g(f"{slug}_equity"))
            # Blank presence is unknown, not "present". The Kaggle data leaves it blank for whole
            # seasons (11-14, 17). Inferring it from who invested would keep the invested rows and
            # drop the passes, inflating offer rates, so unknown rows are excluded uniformly.
            present = flag(g(f"{slug}_present")) if f"{slug}_present" in cols else True
            per_shark[slug] = {
                "present": present,
                "invested": bool((amount or 0) > 0 or (eq or 0) > 0),
                "amount": amount,
                "equity_pct": eq,
            }

        records.append({
            "pitch_id": f"S{int(season):02d}E{int(episode or 0):02d}P{int(pitch_no):02d}",
            "season": int(season),
            "episode": int(episode or 0),
            "air_date": iso_date(g("air_date")),
            "card": card,
            "secret": {
                "name": (g("name") or "").strip(),
                "entrepreneurs": (g("entrepreneurs") or "").strip(),
                "website": (g("website") or "").strip(),
            },
            "outcome": {
                "got_deal": bool(flag(g("got_deal"))),
                "royalty": flag(g("royalty")),
                "loan": num(g("loan")),
                "per_shark": per_shark,
            },
        })
    return records


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        cols, missing = resolve(reader.fieldnames or [])
    if missing:
        raise SystemExit(
            f"Missing required columns: {missing}\nHeaders found: {reader.fieldnames}\n"
            "Add an alias in tank/columns.py if the dataset renamed them."
        )
    return build_records(rows, cols), cols


def save_jsonl(records, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def seen_by(records, slug):
    """Pitches the Shark was known to be on the panel for. Unknown presence is excluded."""
    return [r for r in records if r["outcome"]["per_shark"][slug]["present"] is True]


def split(records, test_seasons, test_on=None):
    """Time-ordered split. Default: the last `test_seasons` seasons are held out.

    `test_on` (e.g. [7, 8]) holds out those seasons instead and trains only on earlier ones,
    so a test window with richer cards can be chosen without training on the future.
    """
    if test_on:
        test_on = set(test_on)
        first = min(test_on)
        return [r for r in records if r["season"] < first], [r for r in records if r["season"] in test_on]
    seasons = sorted({r["season"] for r in records})
    cut = seasons[-test_seasons] if len(seasons) > test_seasons else seasons[-1]
    return [r for r in records if r["season"] < cut], [r for r in records if r["season"] >= cut]


def parse_seasons(text):
    """'7,8' or '5-8' -> [5, 6, 7, 8]; None -> None."""
    if not text:
        return None
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out
