"""Rule checks on the verdicts a Shark model wrote. No model calls, no cost. Runs on any results file.

    python eval/critique_checks.py --shark cuban                       # eval/results/llm_cuban_claude-code.jsonl
    python eval/critique_checks.py --shark cuban --source repeat

What a buyer is paying for is the critique, so each verdict must:
  evidence      cite at least one belief id, and only ids that exist in the profile
  quotes        quote only verified lines (any 4+ word span in quotation marks must be in the profile)
  numbers       use no dollar or percent figure that is not on the pitch card or in its own offer
  structure     have three distinct objections, one hard question that ends with "?", and 2 to 6 sentences of reasoning
  offer         set every offer field to null on OUT, and give an amount and equity (or a loan) on IN
Gate: each check passes on at least 95% of verdicts.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import PROCESSED, ROOT  # noqa: E402
from tank.data import load_jsonl  # noqa: E402
from tank.profiles import load  # noqa: E402
from tank.quotes import found, norm  # noqa: E402

RESULTS = ROOT / "eval" / "results"
BAR = 0.95
QUOTED = re.compile(r"[\"“]([^\"“”]{12,400})[\"”]")
MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(k|m|mm|million|thousand|b|billion)?\b", re.I)
PCT = re.compile(r"(\d+(?:\.\d+)?)\s?%")
SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mm": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}
CHECKS = ("evidence", "quotes", "numbers", "structure", "offer")


def _close(x, allowed, rel=0.05):
    """Rounding is fine ("$13M" for $12.5M). A figure that is on no part of the card is not."""
    return any(a and abs(x - a) <= max(rel * abs(a), 0.5) for a in allowed)


def allowed_numbers(card, verdict):
    money = [card.get(k) for k in ("ask_amount", "implied_valuation", "yearly_revenue", "monthly_revenue")]
    offer = verdict.get("offer") or {}
    money += [offer.get("amount_usd"), offer.get("loan_usd")]
    if offer.get("amount_usd") and offer.get("equity_pct"):
        money.append(offer["amount_usd"] / (offer["equity_pct"] / 100))
    pct = [card.get(k) for k in ("ask_equity_pct", "gross_margin", "net_margin")] + [offer.get("equity_pct")]
    # Figures the founder wrote in the free text ("sells for $10", "90% repeat buyers") are on the card too.
    for field in ("description", "customers", "founder_background", "use_of_funds", "other"):
        text = str(card.get(field) or "")
        money += [float(m.group(1).replace(",", "")) * SCALE.get((m.group(2) or "").lower(), 1) for m in MONEY.finditer(text)]
        pct += [float(m.group(1)) for m in PCT.finditer(text)]
    return [m for m in money if isinstance(m, (int, float))], [p for p in pct if isinstance(p, (int, float))]


def invented_numbers(text, card, verdict):
    money_ok, pct_ok = allowed_numbers(card, verdict)
    bad = []
    for m in MONEY.finditer(text):
        v = float(m.group(1).replace(",", "")) * SCALE.get((m.group(2) or "").lower(), 1)
        if not _close(v, money_ok):
            bad.append(m.group(0).strip())
    for m in PCT.finditer(text):
        if not _close(float(m.group(1)), pct_ok, rel=0.0):
            bad.append(m.group(0))
    return bad


def check(verdict, card, profile):
    """-> {check: None if it passes, else a short reason}."""
    belief_ids = {b["id"] for b in profile["beliefs"]}
    bank = " | ".join(norm(q["text"]) for b in profile["beliefs"] + profile.get("misfires", []) for q in b.get("quotes", []))
    text = " ".join([verdict.get("reasoning", ""), verdict.get("grill_question", "")] + list(verdict.get("objections", [])))
    out = {}

    cited = [e for e in verdict.get("evidence", []) if e in belief_ids]
    unknown = [e for e in verdict.get("evidence", []) if not e.startswith(("P", "p-")) and e not in belief_ids
               and re.fullmatch(r"[a-z0-9-]+", e)]
    out["evidence"] = None if cited and not unknown else (f"unknown ids {unknown}" if unknown else "no belief id cited")

    bad_q = [q for q in QUOTED.findall(text) if len(norm(q).split()) >= 4 and not found(q, bank)]
    out["quotes"] = f"unverified quote: {bad_q[0][:60]}" if bad_q else None

    bad_n = invented_numbers(text, card, verdict)
    out["numbers"] = f"not on the card: {bad_n[:3]}" if bad_n else None

    objs = [o.strip().lower() for o in verdict.get("objections", []) if o.strip()]
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", verdict.get("reasoning", "").strip()) if s]
    problems = []
    if len(objs) != 3 or len(set(objs)) != 3:
        problems.append(f"{len(set(objs))} distinct objections")
    if not verdict.get("grill_question", "").strip().endswith("?"):
        problems.append("hard question has no '?'")
    if not 2 <= len(sentences) <= 6:
        problems.append(f"{len(sentences)} sentences of reasoning")
    out["structure"] = "; ".join(problems) or None

    offer = verdict.get("offer") or {}
    if verdict.get("decision") == "out":
        filled = [k for k in ("amount_usd", "equity_pct", "royalty", "loan_usd") if offer.get(k) not in (None, "", "none")]
        out["offer"] = f"OUT with offer fields {filled}" if filled else None
    else:
        has_terms = (offer.get("amount_usd") and offer.get("equity_pct") is not None) or offer.get("loan_usd")
        out["offer"] = None if has_terms else "IN with no amount and equity"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shark", required=True)
    ap.add_argument("--model", default="claude-code")
    ap.add_argument("--source", default="llm", choices=["llm", "repeat"])
    ap.add_argument("--data", default=str(PROCESSED))
    args = ap.parse_args()
    path = RESULTS / f"{args.source}_{args.shark}_{args.model}.jsonl"
    if not path.exists():
        raise SystemExit(f"No results at {path.relative_to(ROOT).as_posix()}")
    profile = load(args.shark)
    cards = {r["pitch_id"]: r["card"] for r in load_jsonl(args.data)}
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("verdict")]
    results = [(r["pitch_id"], check(r["verdict"], cards[r["pitch_id"]], profile)) for r in rows]

    n = len(results)
    out = [f"# Critique checks: {args.shark} on {args.model} ({args.source})", "", "| check | pass rate | bar |", "|---|---|---|"]
    failed = []
    for c in CHECKS:
        rate = sum(1 for _, res in results if res[c] is None) / n
        out.append(f"| {c} | {rate:.1%} | >= {BAR:.0%} |")
        if rate < BAR:
            failed.append(c)
    verdict = "PASS" if not failed else f"FAIL ({', '.join(failed)})"
    out[1:1] = ["", f"**Verdict: {verdict}** on {n} verdicts."]
    out += ["", "## Examples of failures", ""]
    for c in CHECKS:
        ex = [(pid, res[c]) for pid, res in results if res[c]][:3]
        for _, why in ex:
            out.append(f"- {c}: {why}")
    report = "\n".join(out) + "\n"
    dest = RESULTS / f"critique_{args.shark}_{args.model}.md"
    dest.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {dest.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
