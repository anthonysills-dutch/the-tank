"""Build the customer package: an AI-neutral folder of markdown files, plus a zip.

    python scripts/build_package.py

Static, hand-written files (README, INSTALLER, OPERATIONS-MANUAL, procedures, templates, tests) live
in package_src/ and are written in ASD-STE100 Simplified Technical English. This script generates the
rest from the verified data, so the package can never drift from what the checks passed:

    system/sharks/<slug>.md        beliefs, verified quotes, misfires, deal record (full data)
    system/precedents/<slug>.md    every past pitch that Shark heard, anonymized, grouped by industry
    system/precedents/INDUSTRIES.md
    system/checks/quote-bank.md    every verified quote, for checking output
    upload-pack/                   the same system in 7 files for chat assistants with projects
    LICENSES.md, MANIFEST.md, workspace/

Refuses to build if any profile fails validation or any quote fails verification.
Output: dist/the-tank/ and dist/the-tank-v<version>.zip
"""

import re
import shutil
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import DATA_DIR, PROCESSED, ROOT  # noqa: E402
from tank.columns import SHARKS  # noqa: E402
from tank.data import load_jsonl, seen_by  # noqa: E402
from tank.precedents import describe_outcome, opaque_id  # noqa: E402
from tank.profiles import load, sourced_slugs  # noqa: E402
from tank.quotes import check_profile  # noqa: E402
from tank.stats import shark_stats  # noqa: E402

SRC = ROOT / "package_src"
DIST = ROOT / "dist"
OUT = DIST / "the-tank"
ORDER = ["cuban", "oleary", "corcoran", "greiner", "herjavec", "john"]
SHORT = {"cuban": "Cuban", "oleary": "O'Leary", "corcoran": "Corcoran", "greiner": "Greiner",
         "herjavec": "Herjavec", "john": "John"}


def money(v):
    return f"${v:,.0f}" if isinstance(v, (int, float)) else "not disclosed"


def shark_md(p, stats):
    s = p["slug"]
    srcs = {x["id"]: x for x in p["sources"]}
    lines = [
        f"# Shark Model: {SHORT[s]}",
        "",
        f"This file is the {SHORT[s]} model. It uses the public record of {p['name']}. "
        f"It is a simulation. It is not {p['name']} and does not speak for {p['name']}.",
        "",
        f"- **Lens:** {p['lens']}",
        f"- **Tenure:** {p['tenure_note']}",
        f"- **Profile version:** {p['version']}, reviewed {p['reviewed']}",
        "",
        "## Beliefs",
        "",
        "Each belief has an ID. Write the ID in the evidence of a verdict. "
        "The quoted lines are verified word for word. Quote only these lines.",
        "",
    ]
    for b in p["beliefs"]:
        lines += [f"### `{b['id']}` ({b['weight']})", "", b["claim"], "", f"**How it applies:** {b['applies_as']}", ""]
        if b["confidence"] == "derived-from-deals":
            lines += ["**Basis:** the deal record in this file, not a quote.", ""]
        for q in b.get("quotes", []):
            d = srcs[q["source"]].get("date", "")
            lines.append(f'> "{q["text"]}" ({q["source"]}{", " + d if d and d != "unknown" else ""})')
        lines.append("")
    lines += ["## Where this lens misfires", "", "If one of these items applies to the pitch, adjust the judgment and say so.", ""]
    for m in p["misfires"]:
        lines.append(f"- {m['claim']}")
        for q in m.get("quotes", []):
            lines.append(f'  > "{q["text"]}" ({q["source"]})')
    lines += ["", "## Dealbreakers", "", "A dealbreaker that applies gives OUT.", ""]
    lines += [f"- {d['claim']} (from: {', '.join(d.get('from', []))})" for d in p.get("dealbreakers", [])]
    lines += ["", "## Deal record", "", f"Source: on-air decisions on pitches where {p['name']} was on the panel (see `LICENSES.md`).", ""]
    lines.append(f"- Offers made: {stats['deals']} of {stats['pitches_seen']} pitches seen ({stats['invest_rate']:.0%}). Most pitches get OUT.")
    if stats.get("median_amount"):
        lines.append(f"- Typical offer: {money(stats['median_amount'])} for {stats['median_equity_pct']:g}% equity (median).")
    if stats.get("solo_deal_share") is not None:
        lines.append(f"- Deals done with no other Shark: {stats['solo_deal_share']:.0%}.")
    if stats.get("royalty_deal_share") is not None:
        lines.append(f"- Deals with a royalty part: {stats['royalty_deal_share']:.0%}.")
    for label, key in (("Highest offer rates", "most_receptive_industries"), ("Lowest offer rates", "least_receptive_industries")):
        if stats.get(key):
            lines.append(f"- {label} by industry: " + "; ".join(
                f"{d['industry']} {d['invest_rate']:.0%} of {d['seen']}" for d in stats[key]) + ".")
    lines += ["", "## Negotiation record", "",
              "Tank mode uses this section. It shows how this investor negotiated on air.", ""]
    if stats.get("median_valuation_vs_ask") is not None:
        lines.append(f"- Deal valuation compared with the founder's asked valuation: {stats['median_valuation_vs_ask']:g} times "
                     f"(median of {stats['valuation_ratio_n']} deals). Below 1 means more equity for the same money.")
    if stats.get("paid_full_ask_share") is not None:
        lines.append(f"- Deals at the full asked valuation or higher: {stats['paid_full_ask_share']:.0%}.")
    if stats.get("partners"):
        lines.append("- Partners in shared deals: " + "; ".join(
            f"{SHORT[x['shark']]} {x['deals_together']}" for x in stats["partners"]) + ".")
    lines += ["", "## Sources", "", "| ID | Source | Type | Date |", "|---|---|---|---|"]
    lines += [f"| {x['id']} | [{x['title']}]({x['url']}) | {x['kind']} | {x.get('date', '')} |" for x in p["sources"]]
    return "\n".join(lines) + "\n"


def dedupe(text):
    """Merged sources often repeat the short descriptor inside the long one: 'X . X, and more'."""
    parts = [p.strip() for p in re.split(r"\s*\.\s+", text) if p.strip()]
    kept = []
    for p in parts:
        low = p.lower().rstrip(".")
        if any(low in k.lower() for k in kept) or not low:
            continue
        kept = [k for k in kept if k.lower().rstrip(".") not in low]
        kept.append(p)
    return ". ".join(kept)


def precedents_md(records, slug, name):
    seen = seen_by(records, slug)
    by_ind = defaultdict(list)
    for r in seen:
        by_ind[r["card"]["industry"] or "Uncertain/Other"].append(r)
    lines = [
        f"# Past Pitches: {SHORT[slug]} Model",
        "",
        f"These are the on-air pitches that {name} heard, with the company names removed. "
        "Use the section for the industry of the pitch card. Each row: ID | ask | decision | product.",
        "",
    ]
    for ind in sorted(by_ind, key=lambda k: -len(by_ind[k])):
        rows = by_ind[ind]
        offers = sum(1 for r in rows if r["outcome"]["per_shark"][slug]["invested"])
        lines += [f"## {ind}", "", f"{len(rows)} pitches. {offers} got an offer ({offers / len(rows):.0%}).", ""]
        for r in sorted(rows, key=lambda r: r["card"]["ask_amount"] or 0):
            c = r["card"]
            desc = dedupe((c["description"] or "").replace("|", "/"))
            desc = desc if len(desc) <= 220 else desc[:217].rsplit(" ", 1)[0] + "..."
            lines.append(f"- {opaque_id(r['pitch_id'])} | {money(c['ask_amount'])} for {c['ask_equity_pct'] or 0:g}% | "
                         f"{describe_outcome(r, slug)} | {desc}")
        lines.append("")
    return "\n".join(lines)


def industries_md(records):
    counts = defaultdict(int)
    for r in records:
        counts[r["card"]["industry"] or "Uncertain/Other"] += 1
    lines = ["# Industry List", "", "Use one of these names on the pitch card.", "", "| Industry | Past pitches |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    return "\n".join(lines) + "\n"


def quote_bank_md(profiles):
    lines = ["# Quote Bank", "", "Each line is verified word for word against its source. "
             "A Shark model can quote only these lines. If a quote in a verdict is not here, remove it.", ""]
    for p in profiles:
        lines += [f"## {SHORT[p['slug']]} model", ""]
        for b in p["beliefs"] + p["misfires"]:
            for q in b.get("quotes", []):
                lines.append(f'- "{q["text"]}" ({q["source"]})')
        lines.append("")
    return "\n".join(lines)


def licenses_md():
    data_readme = (DATA_DIR / "README.md").read_text(encoding="utf-8")
    start = data_readme.index("## Sources")
    end = data_readme.index("## What the merge checks")
    return ("# Licenses\n\n## Data\n\n" + data_readme[start + len("## Sources"):end].strip() +
            "\n\n## Quotes\n\nThe Shark files contain short verbatim quotes, each with a link to its public source. "
            "The full source texts are not included.\n\n## The rest of the package\n\n"
            "The procedures, templates, and instructions are licensed to the buyer for personal and internal business use.\n")


def build():
    profiles = [load(s) for s in ORDER]
    missing = set(ORDER) - set(sourced_slugs())
    if missing:
        raise SystemExit(f"Not sourced yet: {sorted(missing)}")
    for p in profiles:
        verified, problems = check_profile(p)
        if problems:
            raise SystemExit(f"{p['slug']}: {len(problems)} quotes fail verification. Run scripts/check_quotes.py.")
    records = load_jsonl(PROCESSED)
    version = (SRC / "VERSION").read_text(encoding="utf-8").strip()

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns("VERSION"))
    system = OUT / "system"
    for d in ("sharks", "precedents", "checks"):
        (system / d).mkdir(parents=True, exist_ok=True)

    core = [(OUT / "system" / "START-HERE.md").read_text(encoding="utf-8")]
    for p in profiles:
        s = p["slug"]
        text = shark_md(p, shark_stats(records, s))
        (system / "sharks" / f"{s}.md").write_text(text, encoding="utf-8")
        (system / "precedents" / f"{s}.md").write_text(precedents_md(records, s, p["name"]), encoding="utf-8")
    (system / "precedents" / "INDUSTRIES.md").write_text(industries_md(records), encoding="utf-8")
    (system / "checks" / "quote-bank.md").write_text(quote_bank_md(profiles), encoding="utf-8")
    (OUT / "LICENSES.md").write_text(licenses_md(), encoding="utf-8")
    sessions = OUT / "workspace" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "README.md").write_text("# Sessions\n\nThe AI saves each session in a folder here: `<YYYY-MM-DD>-<short-name>/`.\n", encoding="utf-8")

    # Upload pack: everything except the precedents in one core file, plus one precedents file per Shark.
    pack = OUT / "upload-pack"
    pack.mkdir()
    order = ["procedures/run-a-pitch.md", "procedures/intake.md", "procedures/judge-as-a-shark.md", "procedures/report.md",
             "procedures/tank-mode.md", "templates/pitch-card.md", "templates/verdict.md", "templates/session-report.md",
             "templates/tank-log.md",
             "tests/sample-pitch.md", "tests/self-test-checks.md", "precedents/INDUSTRIES.md", "checks/quote-bank.md"]
    order += [f"sharks/{s}.md" for s in ORDER]
    for rel in order:
        core.append(f"\n\n---\n\n<!-- FILE: {rel} -->\n\n" + (system / rel).read_text(encoding="utf-8"))
    note = ("> This is the upload-pack version. Each file in the file map is a section of this file, "
            "marked `<!-- FILE: path -->`. The past pitches are in the files `PRECEDENTS-<NAME>.md`.\n\n")
    (pack / "TANK-CORE.md").write_text(core[0].replace("\n", "\n\n" + note, 1) + "".join(core[1:]), encoding="utf-8")
    for s in ORDER:
        shutil.copy(system / "precedents" / f"{s}.md", pack / f"PRECEDENTS-{s.upper()}.md")
    (pack / "PROJECT-INSTRUCTIONS.md").write_text(
        "You operate The Tank. The files TANK-CORE.md and PRECEDENTS-<NAME>.md are in your project knowledge. "
        "At the start of each chat, read the section START-HERE at the top of TANK-CORE.md and obey it for the full chat. "
        "When a procedure names a file such as sharks/cuban.md, use the section of TANK-CORE.md marked with that path. "
        "When a procedure names precedents/<name>.md, use the file PRECEDENTS-<NAME>.md. "
        "Do not use web search to find a company, a founder, or the result of a Shark Tank episode.\n", encoding="utf-8")

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    manifest = ["# Manifest", "", f"The Tank, version {version}. {len(files) + 1} files.", "", "| File | Size (KB) |", "|---|---|"]
    manifest += [f"| `{f.relative_to(OUT).as_posix()}` | {f.stat().st_size / 1024:.0f} |" for f in files]
    (OUT / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    zpath = DIST / f"the-tank-v{version}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(p for p in OUT.rglob("*") if p.is_file()):
            z.write(f, Path("the-tank") / f.relative_to(OUT))
    print(f"Built {OUT.relative_to(ROOT).as_posix()} ({len(files) + 1} files) and {zpath.relative_to(ROOT).as_posix()} "
          f"({zpath.stat().st_size / 1024:.0f} KB)")
    for f in sorted((pack).iterdir()):
        print(f"  upload-pack/{f.name}: {f.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    build()
