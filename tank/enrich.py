"""Merge richer per-pitch facts into the base Kaggle records.

Sources (all openly licensed, all optional; whatever is present in data/raw gets used):
  neiljs        Kaggle "All Shark Tank (US) Pitches & Deals", CC0. Seasons 1-8, ~140-char descriptions.
  rahulsathyajit Kaggle "Shark Tank Pitches", CC0. Seasons 1-6, ~130-char descriptions, founder names.
  wikipedia     "Shark Tank season N" articles, CC BY-SA 4.0. Every season: who sat on the panel each
                episode, a few-word product descriptor, YES/NO.

What gets merged:
  description  the longest available text, anonymized like everything else
  presence     Wikipedia's panel line fills Kaggle's blank "Present" cells. Explicit Kaggle values
               are never overwritten. Agreement is measured where both exist, and reported.
Every merged value records its source in record["provenance"].
"""

import csv
import difflib
import json
import re
from collections import defaultdict

from .columns import SHARKS
from .data import anonymize, fix_text

FIRST_NAMES = {"mark": "cuban", "kevin": "oleary", "barbara": "corcoran", "lori": "greiner",
               "robert": "herjavec", "daymond": "john"}


def key(name):
    return re.sub(r"[^a-z0-9]", "", fix_text(name).lower().replace("&", "and"))


# ---------- source readers: each returns {season: [ {name, episode|None, description, ...} ]} ----------

def read_neiljs(path):
    out = defaultdict(list)
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            code = int(r["Season_Epi_code"])
            out[code // 100].append({"name": r["Pitched_Business_Identifier"], "episode": code % 100,
                                     "description": r["Pitched_Business_Desc"], "founders": ""})
    return out


def read_rahul(path):
    out = defaultdict(list)
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            out[int(r["season"])].append({"name": r["title"], "episode": int(r["episode"]),
                                          "description": r["description"], "founders": r["entrepreneurs"]})
    return out


def _unwiki(s):
    s = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    return s.replace("''", "").strip()


def parse_wiki_season(wikitext):
    """-> list of episodes: {episode, panel: set(slugs) | None, pitches: [{name, description, deal}]}"""
    episodes = []
    for block in re.split(r"\{\{#invoke:Episode list|\{\{Episode list", wikitext)[1:]:
        ep = re.search(r"\|\s*EpisodeNumber2\s*=\s*(\d+)", block)
        summ = re.search(r"\|\s*ShortSummary\s*=(.*?)(?:\n\s*\|\s*LineColor|\n\}\})", block, re.S)
        if not ep or not summ:
            continue
        text = _unwiki(summ.group(1))
        panel = None
        m = re.search(r"Sharks?:\s*([^<\n]*)", text)
        if m:
            names = [n.strip().lower() for n in m.group(1).split(",")]
            panel = {FIRST_NAMES[n] for n in names if n in FIRST_NAMES}
            if len(names) < 4:  # "Guest Shark: X" lines don't list the full panel
                panel = None
        body = re.sub(r".*?<br\s*/?>", "", text, count=1, flags=re.S) if "<br" in text else text
        pitches = []
        for name, rest in re.findall(r'"([^"]+)"\s*([^;"]*)', body):
            deal = re.search(r"\((YES|NO)\)", rest, re.I)
            desc = re.sub(r"\([^)]*\)", "", rest).strip(" .,-")
            pitches.append({"name": name, "description": desc, "deal": deal.group(1).upper() == "YES" if deal else None})
        for name, rest in re.findall(r"^\*\s*([^:\n]+):\s*([^\n]+)", body, re.M):
            pitches.append({"name": name, "description": re.sub(r"\([^)]*\)", "", rest).strip(" .,-"), "deal": None})
        episodes.append({"episode": int(ep.group(1)), "panel": panel, "pitches": pitches})
    return episodes


def read_wikipedia(folder):
    seasons, revs = {}, {}
    for path in sorted(folder.glob("season_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))["parse"]
        except (ValueError, KeyError):
            continue
        s = int(path.stem.split("_")[1])
        seasons[s] = parse_wiki_season(data["wikitext"])
        revs[s] = data.get("revid")
    return seasons, revs


# ---------- matching ----------

def match(record, candidates, cutoff=0.85):
    """Best candidate in the same season: exact name key first, then fuzzy, preferring the same episode."""
    rk = key(record["secret"]["name"])
    if not rk:
        return None
    exact = [c for c in candidates if key(c["name"]) == rk]
    pool = exact or [c for c in candidates if difflib.SequenceMatcher(None, rk, key(c["name"])).ratio() >= cutoff]
    if not pool:
        return None
    same_ep = [c for c in pool if c.get("episode") == record["episode"]]
    return (same_ep or pool)[0]


def enrich(records, raw_dir):
    report = defaultdict(int)
    text_sources = []
    for fname, reader, label in (("neiljs_pitches_deals.csv", read_neiljs, "neiljs"),
                                 ("rahulsathyajit_pitches.csv", read_rahul, "rahulsathyajit")):
        path = raw_dir / "sources" / fname
        if path.exists():
            text_sources.append((label, reader(path)))
    wiki, revs = read_wikipedia(raw_dir / "wikipedia")
    wiki_pitches = {s: [dict(p, episode=e["episode"]) for e in eps for p in e["pitches"]] for s, eps in wiki.items()}
    wiki_panels = {(s, e["episode"]): e["panel"] for s, eps in wiki.items() for e in eps if e["panel"]}

    agree = disagree = 0
    for r in records:
        prov = r.setdefault("provenance", {"description": "kaggle-thirumani"})
        best, best_src, founders = r["card"]["description"], "kaggle-thirumani", r["secret"]["entrepreneurs"]
        options = [(label, match(r, src.get(r["season"], []))) for label, src in text_sources]
        options.append(("wikipedia", match(r, wiki_pitches.get(r["season"], []))))
        for label, hit in options:
            if not hit:
                continue
            report[f"matched_{label}"] += 1
            founders = ", ".join(x for x in (founders, hit.get("founders")) if x)
            if label == "wikipedia" and hit.get("deal") is not None:
                report["wiki_deal_checked"] += 1
                report["wiki_deal_agrees"] += int(hit["deal"] == r["outcome"]["got_deal"])
            if len(hit["description"] or "") > len(best or ""):
                best, best_src = hit["description"], label
        if best_src != "kaggle-thirumani":
            r["card"]["description"] = anonymize(best, r["secret"]["name"], founders, r["secret"]["website"])
            prov["description"] = best_src
            report[f"description_from_{best_src}"] += 1

        panel = wiki_panels.get((r["season"], r["episode"]))
        if panel is None:
            continue
        for slug in SHARKS:
            s = r["outcome"]["per_shark"][slug]
            wiki_says = slug in panel
            if s["present"] is None:
                s["present"] = wiki_says
                prov.setdefault("presence_filled", []).append(slug)
                report["presence_filled"] += 1
            elif s["present"] == wiki_says:
                agree += 1
            else:
                disagree += 1
            if s["invested"] and s["present"] is False:
                report["invested_but_absent"] += 1

    report["presence_agree"], report["presence_disagree"] = agree, disagree
    report["wikipedia_revisions"] = revs
    return dict(report)
